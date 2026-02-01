from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas
from datetime import datetime
import os
import json

router = APIRouter()

REPORT_BASE_DIR = "/app/reports"


# 1. 触发接口 (前端调用)
@router.post("/dispatch/{case_id}", response_model=schemas.TestReportOut)
def dispatch_task(case_id: int, db: Session = Depends(get_db)):
    # 检查用例是否存在
    case = db.query(models.TestCase).filter(models.TestCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Test case not found")

    # 创建一条 Pending 状态的报告记录作为“任务”
    new_report = models.TestReport(
        test_case_id=case_id,
        status=models.TaskStatus.PENDING,
        script_content=case.script_content  # 快照保存当前脚本
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)
    return new_report


# 2. 执行器领任务接口 (Executor 调用)
@router.get("/tasks/pop")
def pop_task(db: Session = Depends(get_db)):
    # 使用 with_for_update 锁定行，防止并发冲突 (需数据库支持，如PG/MySQL)
    # 查找最早的一条 pending 任务
    task = db.query(models.TestReport) \
        .filter(models.TestReport.status == models.TaskStatus.PENDING) \
        .order_by(models.TestReport.id.asc()) \
        .with_for_update(skip_locked=True) \
        .first()

    if not task:
        return None

    # 标记为运行中
    task.status = models.TaskStatus.RUNNING
    task.start_time = datetime.now()
    db.commit()

    # 获取关联信息
    case = task.test_case
    project_owner = case.project.owner

    # 查找该用户的 LLM 配置 (优先取执行配置)
    llm_config = db.query(models.LLMConfig) \
        .filter(models.LLMConfig.user_id == project_owner.id, models.LLMConfig.is_active_exec == True) \
        .first()

    if not llm_config:
        # 如果没有专门的执行配置，取第一个可用的
        llm_config = db.query(models.LLMConfig) \
            .filter(models.LLMConfig.user_id == project_owner.id) \
            .first()

    api_key = llm_config.api_key if llm_config else ""

    # 返回任务包
    return {
        "id": task.id,
        "script": task.script_content,
        "llm_config": {
            "api_key": api_key,
            "model": llm_config.model_name if llm_config else "gpt-4o"
        }
    }


# 3. 报告上传接口 (Executor 调用)
@router.post("/tasks/{task_id}/report")
def upload_report(task_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    report = db.query(models.TestReport).filter(models.TestReport.id == task_id).first()
    if not report:
        raise HTTPException(404, "Report not found")

    # 更新状态
    report.status = data.get("status", "failed")
    report.logs = data.get("logs", "")
    report.end_time = datetime.now()

    # 处理 HTML 报告存储
    if "html_report" in data and data["html_report"]:
        # 目录结构: /app/reports/run_{id}/report.html
        task_dir_name = f"run_{task_id}"
        abs_path = os.path.join(REPORT_BASE_DIR, task_dir_name)
        os.makedirs(abs_path, exist_ok=True)

        file_path = os.path.join(abs_path, "report.html")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(data["html_report"])

        # 数据库存相对路径，前端通过 /reports/{path} 访问
        report.report_path = f"{task_dir_name}/report.html"

    db.commit()
    return {"status": "ok"}