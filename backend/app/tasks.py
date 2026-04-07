import os
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from .core.logging import app_logger as logging, setup_logging
from celery import Celery
from .database import SessionLocal
from .models import TestReport, TaskStatus, KnowledgeDocument
from .rag import RagService

# 配置 Celery
celery_app = Celery('midscene_worker', broker='redis://redis:6379/0')

# [修改] 使用 /data 目录，配合 Docker 的 volume 挂载，防止污染 backend 代码目录
REPORT_DIR = "/data/reports"


@celery_app.task
def run_midscene_task(report_id: int, llm_config: dict):
    """
    执行 Midscene 任务 (增强版实时日志)
    """
    # 确保工作进程使用正确的日志配置
    setup_logging()
    logging.info(f"🚀 [任务开始] 报告编号: {report_id}")
    db = SessionLocal()
    report = db.query(TestReport).filter(TestReport.id == report_id).first()

    if not report:
        logging.error(f"报告 {report_id} 没有找到")
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
        # --- 缓存恢复逻辑 ---
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
                    logging.info(init_log)
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
        env["MIDSCENE_DEBUG_LOG"] = "true"
        env["PYTHONUNBUFFERED"] = "1"
        env["FORCE_COLOR"] = "1"
        env["DEBUG"] = "pw:api"
        env["MIDSCENE_MODEL_REASONING_ENABLED"] = "false"
        
        # --- 构造命令 ---
        if is_ts:
            cmd = ["tsx", script_path]
        else:
            cmd = ["midscene", script_path]

        logging.info(f"正在执行: {' '.join(cmd)}")

        # --- 核心：执行并实时读取 ---
        process = subprocess.Popen(
            cmd,
            cwd=work_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # 实时读取循环
        last_update_time = time.time()
        current_logs = report.logs or ""

        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break

            if line:
                current_logs += line
                # 节流：每 0.5 秒写入一次数据库
                if time.time() - last_update_time > 0.5:
                    report.logs = current_logs
                    db.commit()
                    last_update_time = time.time()

        report.logs = current_logs
        report.end_time = datetime.now()

        # 查找生成的 HTML 报告
        found_html = None
        for root, dirs, files in os.walk(work_dir):
            for file in files:
                if file.endswith(".html"):
                    abs_path = os.path.join(root, file)
                    # 计算相对路径，供前端访问
                    found_html = os.path.relpath(abs_path, REPORT_DIR)
                    break
            if found_html: break

        # --- 结果判定 ---
        if process.returncode == 0:
            report.status = TaskStatus.SUCCESS
            logging.info("Task finished successfully.")

            if found_html:
                report.report_path = found_html
            else:
                report.logs += "\n[系统] 警告：未生成 HTML 报告"
        else:
            report.status = TaskStatus.FAILED
            report.logs += f"\n[系统] 进程已退出，退出码 {process.returncode}"
            logging.error(f"任务执行失败，错误码 {process.returncode}")
            logging.error(f"报告目录 {found_html}")
            # 即使失败也设置 report_path
            if found_html:
                report.report_path = found_html
            else:
                report.logs += "\n[系统] 警告：未生成 HTML 报告"


    except Exception as e:
        logging.exception("任务执行过程中出现异常")
        report.status = TaskStatus.FAILED
        report.logs = (report.logs or "") + f"\n[系统错误] {str(e)}"
        
        # 即使异常也尝试查找 HTML 报告
        found_html = None
        for root, dirs, files in os.walk(work_dir):
            for file in files:
                if file.endswith(".html"):
                    abs_path = os.path.join(root, file)
                    # 计算相对路径，供前端访问
                    found_html = os.path.relpath(abs_path, REPORT_DIR)
                    break
            if found_html: break
        
        if found_html:
            report.report_path = found_html
        else:
            report.logs += "\n[系统] 警告：未生成 HTML 报告"
    finally:
        db.commit()
        db.close()


@celery_app.task
def process_knowledge_file(doc_id: int, llm_config: dict):
    """
    后台任务：处理知识库文件上传与向量化
    """
    # 确保工作进程使用正确的日志配置
    setup_logging()
    db = SessionLocal()
    try:
        doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
        if not doc:
            return

        # 更新状态为解析中
        doc.status = "processing"
        db.commit()

        # 1. 提取配置
        api_key = llm_config.get("api_key")
        base_url = llm_config.get("base_url")
        model_name = llm_config.get("model_name")

        logging.info(f"Task Start: Processing doc {doc_id} with model {model_name}")

        # 2. 初始化 RAG 服务
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

        # 成功时提交
        db.commit()

    except Exception as e:
        # [核心修复] 回滚事务，确保后续的状态更新能成功写入
        db.rollback()
        logging.error(f"Task Failed: {str(e)}")

        # 重新获取对象（rollback 后 session 可能会清理掉之前的对象状态）
        doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
        if doc:
            doc.status = "failed"
            # 截取错误信息，防止过长
            doc.error_msg = str(e)[:200]
            db.commit()

    finally:
        db.close()