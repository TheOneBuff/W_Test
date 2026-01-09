import logging
import os
import shutil
import subprocess
from datetime import datetime, timedelta
from celery import Celery
from .database import SessionLocal
from .models import TestReport, TaskStatus

# 配置 Celery
celery_app = Celery('midscene_worker', broker='redis://redis:6379/0')

REPORT_DIR = "/app/reports"


@celery_app.task
def run_midscene_task(report_id: int, llm_config: dict):
    """
    执行 Midscene 任务
    :param report_id: 报告 ID
    :param llm_config: 包含 api_key, model_name, base_url 等的配置字典
    """
    db = SessionLocal()
    report = db.query(TestReport).filter(TestReport.id == report_id).first()

    # 1. 更新状态为 Running
    report.status = TaskStatus.RUNNING
    db.commit()

    run_id = f"run_{report_id}"
    work_dir = os.path.join(REPORT_DIR, run_id)
    os.makedirs(work_dir, exist_ok=True)

    try:
        # 1. 查找该用例上一次成功的报告
        # 注意：这里需要再次查询 DB，找到同一个 test_case_id 的最近一次 SUCCESS 记录
        last_success_report = db.query(TestReport) \
            .filter(TestReport.test_case_id == report.test_case_id) \
            .filter(TestReport.status == TaskStatus.SUCCESS) \
            .filter(TestReport.id < report_id) \
            .order_by(TestReport.id.desc()) \
            .first()

        if last_success_report:
            last_run_dir = os.path.join(REPORT_DIR, f"run_{last_success_report.id}")
            # 假设缓存固定在 midscene_run/cache 目录下
            last_cache_dir = os.path.join(last_run_dir, "midscene_run", "cache")

            if os.path.exists(last_cache_dir):
                target_cache_dir = os.path.join(work_dir, "midscene_run", "cache")
                try:
                    # 复制整个缓存目录
                    shutil.copytree(last_cache_dir, target_cache_dir, dirs_exist_ok=True)
                    # 追加日志以便调试
                    report.logs = f"系统缓存已从run_{last_success_report.id}恢复\n"
                    logging.info(f"系统缓存已从run_{last_success_report.id}恢复")
                except Exception as e:
                    logging.info(f"系统缓存恢复失败: {e}")

        # 2. 判断脚本类型并写入文件
        is_ts = report.test_case.script_type == 'typescript'
        file_ext = "ts" if is_ts else "yaml"
        script_filename = f"script.{file_ext}"
        script_path = os.path.join(work_dir, script_filename)

        with open(script_path, "w", encoding='utf-8') as f:
            f.write(report.script_content)

        # 3. 核心：构建环境变量 (修复 'env' 未定义的问题)
        env = os.environ.copy()  # <--- 必须先创建 env 对象

        # (A) 注入 LLM 参数
        if llm_config.get("api_key"):
            env["OPENAI_API_KEY"] = llm_config.get("api_key")

        if llm_config.get("base_url"):
            env["OPENAI_BASE_URL"] = llm_config.get("base_url")

        if llm_config.get("model_name"):
            env["MIDSCENE_MODEL_NAME"] = llm_config.get("model_name")
        if llm_config.get("model_family"):
            env["MIDSCENE_MODEL_FAMILY"] = llm_config.get("model_family")
            # --- 注入用户自定义环境参数 ---
        custom_env = llm_config.get("custom_env", {})
        for k, v in custom_env.items():
            env[str(k)] = str(v)
        # (B) 设置 Node 路径 (确保能找到全局安装的 npm 包)
        # Playwright 镜像基于 Ubuntu，通常在 /usr/lib/node_modules 或 /usr/local/lib/node_modules
        # 我们这里把两个都加上以防万一
        env["NODE_PATH"] = "/usr/lib/node_modules:/usr/local/lib/node_modules"

        # 4. 构造执行命令
        if is_ts:
            # TypeScript 模式：使用 tsx 直接运行
            cmd = ["tsx", script_path]
        else:
            # YAML 模式：使用 midscene cli
            cmd = ["midscene", script_path]

        # 5. 执行子进程
        process = subprocess.Popen(
            cmd,
            cwd=work_dir,
            env=env,  # <--- 注入环境变量
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout, stderr = process.communicate()

        # 6. 处理结果
        report.logs = f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"
        # 容器镜像不带时区，在这里直接处理加8小时
        report.end_time = datetime.now() + timedelta(hours=8)

        if process.returncode == 0:
            report.status = TaskStatus.SUCCESS

            # 递归查找生成的 HTML 报告 (支持 Midscene 生成在子目录的情况)
            found_html = None
            for root, dirs, files in os.walk(work_dir):
                for file in files:
                    if file.endswith(".html"):
                        # 计算相对路径，例如: run_123/report/report.html
                        abs_path = os.path.join(root, file)
                        rel_path = os.path.relpath(abs_path, REPORT_DIR)
                        found_html = rel_path
                        break
                if found_html:
                    break

            if found_html:
                report.report_path = found_html
            else:
                # 兼容情况：虽然成功了但没找到报告，可能是 Prompt 模式
                report.logs += "\n\n系统任务已完成，但未找到HTML报告"
                logging.info(f"系统任务已完成，但未找到HTML报告")

        else:
            report.status = TaskStatus.FAILED

    except Exception as e:
        report.status = TaskStatus.FAILED
        report.logs = f"网络错误: {str(e)}"
    finally:
        db.commit()
        db.close()
