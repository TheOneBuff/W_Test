import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import models, schemas
from ..database import get_db
from .auth import get_current_user
from ..tasks import run_midscene_task  # 引入 Celery 任务
from sqlalchemy import desc

router = APIRouter()


def check_case_permission(case: models.TestCase, user: models.User):
    """
    检查用户是否有权限操作该用例
    规则：Admin 可以操作所有；普通用户只能操作自己项目下的用例
    """
    if user.username == "admin":
        return True

    # 如果用例没有关联项目，或者关联的项目的 Owner 不是当前用户
    if not case.project or case.project.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有权限访问此用例 (不属于您的项目)"
        )

# 1. 获取列表
@router.get("/", response_model=List[schemas.TestCaseOut])
def get_test_cases(
        project_id: Optional[int] = None,  # 支持按项目筛选
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.TestCase)

    # JOIN 项目表以便过滤
    query = query.outerjoin(models.Project, models.TestCase.project_id == models.Project.id)

    # 权限过滤：如果是普通用户，只返回自己项目下的用例
    if current_user.username != "admin":
        # 逻辑：(属于我的项目) OR (项目为空且我是创建者? 暂时不支持孤儿用例，直接过滤)
        query = query.filter(models.Project.owner_id == current_user.id)

    # 前端筛选参数
    if project_id:
        query = query.filter(models.TestCase.project_id == project_id)

    return query.all()



# 2. 获取详情
@router.get("/{case_id}", response_model=schemas.TestCaseOut)
def get_test_case(
        case_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    case = db.query(models.TestCase).filter(models.TestCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Not found")

    # 检查权限
    check_case_permission(case, current_user)

    return case


# 3. 创建
@router.post("/", response_model=schemas.TestCaseOut)
def create_test_case(
        case: schemas.TestCaseCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # 如果指定了项目，必须检查该项目是否属于当前用户
    if case.project_id:
        project = db.query(models.Project).filter(models.Project.id == case.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if current_user.username != "admin" and project.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="您不能在别人的项目中创建用例")

    db_case = models.TestCase(**case.dict())
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case


# 4. 更新
@router.put("/{case_id}", response_model=schemas.TestCaseOut)
def update_test_case(
        case_id: int,
        case_in: schemas.TestCaseCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    case = db.query(models.TestCase).filter(models.TestCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Not found")

    # 检查是否有权修改当前用例
    check_case_permission(case, current_user)

    # 如果试图转移项目 (修改 project_id)，也要检查目标项目是否属于用户
    if case_in.project_id and case_in.project_id != case.project_id:
        target_project = db.query(models.Project).filter(models.Project.id == case_in.project_id).first()
        if current_user.username != "admin" and target_project.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="不能将用例转移到他人的项目")

    # 更新字段
    for field, value in case_in.dict(exclude_unset=True).items():
        setattr(case, field, value)

    db.commit()
    db.refresh(case)
    return case


# 5. 删除
@router.delete("/{case_id}")
def delete_test_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    case = db.query(models.TestCase).filter(models.TestCase.id == case_id).first()
    if case:
        check_case_permission(case, current_user) # 权限检查
        db.delete(case)
        db.commit()
    return {"status": "success"}


# --- 核心：执行测试 ---
@router.post("/{case_id}/run", response_model=schemas.TestReportOut)
def run_test_case(
    case_id: int,
    env_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    case = db.query(models.TestCase).filter(models.TestCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    check_case_permission(case, current_user)

    # 1. 获取用户的大模型配置
    llm_config = current_user.llm_config
    if not llm_config or not llm_config.api_key:
        raise HTTPException(status_code=400, detail="请先配置大模型参数 (API Key)")

    # 获取环境遍历
    env_vars = {}
    if env_id:
        env_obj = db.query(models.Environment).filter(models.Environment.id == env_id).first()
        if env_obj:
            import json
            try:
                env_vars = json.loads(env_obj.variables)
            except:
                pass
    # 2. 准备配置字典 (将用于注入环境变量)
    # 将 env_vars 合并到 llm_env_vars 中，传递给 Celery
    # 这一步将 DB 中的字段映射为简单的字典传递给 Worker
    llm_env_vars = {
        "api_key": llm_config.api_key,
        "model_name": llm_config.model_name or "gpt-4o",
        "base_url": llm_config.base_url or "",
        "provider": llm_config.provider or "openai",
        "model_family": llm_config.model_family,
        "custom_env": env_vars
    }
    new_report = models.TestReport(
        test_case_id=case.id,
        status=models.TaskStatus.PENDING,
        script_content=case.script_content,
        start_time=datetime.now() + timedelta(hours=8),
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    # 3. 触发任务，传递配置字典
    run_midscene_task.delay(new_report.id, llm_env_vars)

    return new_report


# 6. 获取报告详情（用于轮询状态）
@router.get("/reports/{report_id}", response_model=schemas.TestReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(models.TestReport).filter(models.TestReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/reports/", response_model=List[schemas.TestReportOut])
def get_reports(
        skip: int = 0,
        limit: int = 20,
        status: Optional[models.TaskStatus] = None,
        case_id: Optional[int] = None,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.TestReport)

    # 关联查询，以便后续可能的权限过滤（如果是普通用户，只能看自己项目的报告）
    query = query.join(models.TestCase).join(models.Project)

    if current_user.username != "admin":
        query = query.filter(models.Project.owner_id == current_user.id)

    if status:
        query = query.filter(models.TestReport.status == status)
    if case_id:
        query = query.filter(models.TestReport.test_case_id == case_id)

    # 按时间倒序
    query = query.order_by(desc(models.TestReport.start_time))
    return query.offset(skip).limit(limit).all()


@router.post("/reports/{report_id}/retry", response_model=schemas.TestReportOut)
def retry_report(
        report_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # 1. 查旧报告
    old_report = db.query(models.TestReport).filter(models.TestReport.id == report_id).first()
    if not old_report:
        raise HTTPException(status_code=404, detail="Report not found")

    # 2. 权限校验
    if current_user.username != "admin":
        if old_report.test_case.project.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Permission denied")

    # 3. 检查 API Key
    llm_config = current_user.llm_config
    if not llm_config or not llm_config.api_key:
        raise HTTPException(status_code=400, detail="请先配置 API Key")

    llm_env_vars = {
        "api_key": llm_config.api_key,
        "model_name": llm_config.model_name,
        "base_url": llm_config.base_url
    }

    # 4. 创建新报告 (复用当时的脚本，或者复用 test_case 最新的脚本？这里选择复用 test_case 最新的，修复 bug 后重跑)
    # 如果想复用当时的脚本，用 old_report.script_content
    new_report = models.TestReport(
        test_case_id=old_report.test_case_id,
        status=models.TaskStatus.PENDING,
        script_content=old_report.test_case.script_content  # 使用最新脚本
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    # 5. 触发 Celery
    run_midscene_task.delay(new_report.id, llm_env_vars)

    return new_report

# 新增调试接口
@router.post("/{case_id}/debug", response_model=schemas.TestReportOut)
def debug_test_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 复用 run 的逻辑，但 status 或者是特殊的 tag
    # 这里我们直接复用 run_test_case 的逻辑
    # 唯一的区别可能是前端拿到 ID 后进入不同的页面
    return run_test_case(case_id, db, current_user)
