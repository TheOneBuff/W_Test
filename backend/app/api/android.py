from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
from datetime import datetime
import json

router = APIRouter()

# 简单的内存队列 (生产环境请用 Redis List)
TASK_QUEUE = []


# 1. 领任务接口
@router.get("/tasks/pop")
def pop_task(db: Session = Depends(get_db)):
    if not TASK_QUEUE:
        return None

    # 取出任务 ID
    task_id = TASK_QUEUE.pop(0)

    # 查询详细信息 (关联用例、环境、LLM配置)
    report = db.query(models.TestReport).filter(models.TestReport.id == task_id).first()
    if not report:
        return None

    case = report.test_case
    owner = case.project.owner  # 假设通过项目关联找到 Owner

    # 组装完整的任务包
    task_payload = {
        "id": report.id,
        "script": case.script_content,
        "env_vars": {},  # 这里可以查 Environment 表注入
        "llm_config": {
            "api_key": owner.llm_config.api_key,
            # ... 其他配置
        }
    }
    return task_payload


# 2. 报告上传接口
@router.post("/tasks/{task_id}/report")
def upload_report(task_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    report = db.query(models.TestReport).filter(models.TestReport.id == task_id).first()
    if not report:
        raise HTTPException(404, "Report not found")

    report.status = data.get("status", "failed")
    report.logs = data.get("logs", "")
    report.end_time = datetime.now()

    # 如果有 HTML 报告内容，保存到文件系统
    if "html_report" in data:
        # 写入文件
        report_dir = f"/app/reports/run_{task_id}"
        import os
        os.makedirs(report_dir, exist_ok=True)
        with open(f"{report_dir}/report.html", "w") as f:
            f.write(data["html_report"])

        report.report_path = f"run_{task_id}/report.html"

    db.commit()
    return {"status": "ok"}


# 3. 触发接口 (前端调用)
@router.post("/dispatch/{case_id}")
def dispatch(case_id: int, db: Session = Depends(get_db)):
    # 创建 Pending 报告
    new_report = models.TestReport(test_case_id=case_id, status="pending")
    db.add(new_report)
    db.commit()

    # 入队
    TASK_QUEUE.append(new_report.id)
    return new_report
