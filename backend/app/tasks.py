import logging
import os
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from celery import Celery
from .database import SessionLocal
from .models import TestReport, TaskStatus, KnowledgeDocument
from .rag import RagService

# 配置 Celery
celery_app = Celery('midscene_worker', broker='redis://redis:6379/0')

REPORT_DIR = "/app/reports"


@celery_app.task
def run_midscene_task(report_id: int, llm_config: dict):
    """
    执行 Midscene 任务 (增强版实时日志)
    """
    logging.info(f"🚀 [Task Started] Report ID: {report_id}")
    db = SessionLocal()
    report = db.query(TestReport).filter(TestReport.id == report_id).first()

    if not report:
        logging.error(f"Report {report_id} not found.")
        db.close()
        return

    # 1. 更新状态为 Running
    report.status = TaskStatus.RUNNING
    if report.logs is None:
        report.logs = ""
    db.commit()

    run_id = f"run_{report_id}"
    work_dir = os.path.join(REPORT_DIR, run_id)
    os.makedirs(work_dir, exist_ok=True)

    try:
        # --- 缓存恢复逻辑 (保持不变) ---
        last_success_report = db.query(TestReport) \
            .filter(TestReport.test_case_id == report.test_case_id) \
            .filter(TestReport.status == TaskStatus.SUCCESS) \
            .filter(TestReport.id < report_id) \
            .order_by(TestReport.id.desc()) \
            .first()

        if last_success_report:
            last_run_dir = os.path.join(REPORT_DIR, f"run_{last_success_report.id}")
            last_cache_dir = os.path.join(last_run_dir, "midscene_run", "cache")
            if os.path.exists(last_cache_dir):
                target_cache_dir = os.path.join(work_dir, "midscene_run", "cache")
                try:
                    shutil.copytree(last_cache_dir, target_cache_dir, dirs_exist_ok=True)
                    init_log = f"系统缓存已从run_{last_success_report.id}恢复\n"
                    report.logs += init_log
                except Exception as e:
                    logging.warning(f"缓存恢复失败: {e}")

        # --- 写入脚本 ---
        is_ts = report.test_case.script_type == 'typescript'
        file_ext = "ts" if is_ts else "yaml"
        script_filename = f"script.{file_ext}"
        script_path = os.path.join(work_dir, script_filename)

        with open(script_path, "w", encoding='utf-8') as f:
            f.write(report.script_content)

        # --- 环境变量配置 ---
        env = os.environ.copy()
        # 基础 LLM 配置
        if llm_config.get("api_key"): env["OPENAI_API_KEY"] = llm_config.get("api_key")
        if llm_config.get("base_url"): env["OPENAI_BASE_URL"] = llm_config.get("base_url")
        if llm_config.get("model_name"): env["MIDSCENE_MODEL_NAME"] = llm_config.get("model_name")
        if llm_config.get("model_family"): env["MIDSCENE_MODEL_FAMILY"] = llm_config.get("model_family")

        # 用户自定义变量
        custom_env = llm_config.get("custom_env", {})
        for k, v in custom_env.items():
            env[str(k)] = str(v)

        # 关键配置：强制开启调试日志并尝试禁用缓冲
        env["NODE_PATH"] = "/usr/lib/node_modules:/usr/local/lib/node_modules"
        env["MIDSCENE_DEBUG_LOG"] = "true"  # 让 Midscene 输出更多细节
        env["PYTHONUNBUFFERED"] = "1"  # Python 无缓冲
        env["FORCE_COLOR"] = "1"  # 保留颜色代码(可选，有时有助于输出)
        env["DEBUG"] = "pw:api"  # 开启 Playwright 的 API 级调试日志

        # --- 构造命令 ---
        if is_ts:
            cmd = ["tsx", script_path]
        else:
            cmd = ["midscene", script_path]

        logging.info(f"Executing: {' '.join(cmd)}")

        # --- 核心：执行并实时读取 ---
        process = subprocess.Popen(
            cmd,
            cwd=work_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # 合并输出流
            text=True,
            bufsize=1,  # 行缓冲
            universal_newlines=True
        )

        # 实时读取循环
        last_update_time = time.time()
        current_logs = report.logs or ""

        # 使用 readline 逐行读取，直到进程结束
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break

            if line:
                current_logs += line

                # 节流：每 0.5 秒写入一次数据库，避免 IO 过高
                if time.time() - last_update_time > 0.5:
                    report.logs = current_logs
                    db.commit()
                    # logging.info(f"Log updated... ({len(current_logs)} chars)") # 调试用
                    last_update_time = time.time()

        # 循环结束后，确保最后的内容被写入
        report.logs = current_logs

        # --- 任务结果处理 ---
        report.end_time = datetime.now()

        if process.returncode == 0:
            report.status = TaskStatus.SUCCESS
            logging.info("Task finished successfully.")
            # 查找报告
            found_html = None
            for root, dirs, files in os.walk(work_dir):
                for file in files:
                    if file.endswith(".html"):
                        abs_path = os.path.join(root, file)
                        found_html = os.path.relpath(abs_path, REPORT_DIR)
                        break
                if found_html: break

            if found_html:
                report.report_path = found_html
            else:
                report.logs += "\n[System] Warning: No HTML report generated."
        else:
            report.status = TaskStatus.FAILED
            report.logs += f"\n[System] Process exited with code {process.returncode}"
            logging.error(f"Task failed with code {process.returncode}")

    except Exception as e:
        logging.exception("Exception during task execution")
        report.status = TaskStatus.FAILED
        report.logs = (report.logs or "") + f"\n[System Error] {str(e)}"
    finally:
        db.commit()
        db.close()


@celery_app.task
def process_knowledge_file(doc_id: int, llm_config: dict):
    db = SessionLocal()
    try:
        doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
        if not doc:
            return

        # 更新状态为解析中
        doc.status = "processing"
        db.commit()

        # 1. 从字典中提取配置
        api_key = llm_config.get("api_key")
        base_url = llm_config.get("base_url")
        model_name = llm_config.get("model_name")  # <--- 获取 model_name

        logging.info(f"Task Start: Processing doc {doc_id} with model {model_name}")

        # 2. 初始化 RAG 服务 (传入 model_name)
        rag = RagService(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name
        )

        # 3. 执行解析
        chunks_count = rag.process_document(doc.file_path)

        # 4. 更新结果
        if chunks_count > 0:
            doc.status = "success"
            doc.chunk_count = chunks_count
            doc.error_msg = None
        else:
            doc.status = "failed"
            doc.error_msg = "未提取到有效文本或解析后为空"

    except Exception as e:
        logging.error(f"Task Failed: {str(e)}")
        doc.status = "failed"
        # 截取前200个字符作为错误信息存入数据库
        doc.error_msg = str(e)[:200]
    finally:
        db.commit()
        db.close()