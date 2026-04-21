import logging
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
from .. import models, schemas
from ..database import get_db
from .auth import get_current_user
from ..tasks import run_midscene_task, notify_batch_result
from sqlalchemy import desc, true

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


# 辅助函数：转换 Report ORM 对象 -> Pydantic Schema，并填充 test_case_name
def report_to_schema(report_obj: models.TestReport) -> schemas.TestReportOut:
    # model_validate 会根据 from_attributes=True 从 ORM 对象读取字段
    dto = schemas.TestReportOut.model_validate(report_obj)
    # 手动填充需要关联查询的字段
    if report_obj.test_case:
        dto.test_case_name = report_obj.test_case.name
    return dto


# 1. 获取列表
@router.get("/", response_model=List[schemas.TestCaseOut])
def get_test_cases(
        project_id: Optional[int] = None,  # 支持按项目筛选
        case_type: Optional[str] = None,  # 支持按类型筛选: web / pc
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.TestCase)

    # [优化] 使用显式连接条件
    query = query.outerjoin(models.Project, models.TestCase.project_id == models.Project.id)

    # 权限过滤
    if current_user.username != "admin":
        query = query.filter(models.Project.owner_id == current_user.id)

    # 前端筛选参数
    if project_id:
        query = query.filter(models.TestCase.project_id == project_id)

    # 类型筛选
    if case_type:
        query = query.filter(models.TestCase.case_type == case_type)

    items = query.all()

    # 填充 project_name (可选优化)
    results = []
    for item in items:
        dto = schemas.TestCaseOut.model_validate(item)
        if item.project:
            dto.project_name = item.project.name
        results.append(dto)

    return results


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

    check_case_permission(case, current_user)

    dto = schemas.TestCaseOut.model_validate(case)
    if case.project:
        dto.project_name = case.project.name
    return dto


# 3. 创建
@router.post("/", response_model=schemas.TestCaseOut)
def create_test_case(
        case: schemas.TestCaseCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    if case.project_id:
        project = db.query(models.Project).filter(models.Project.id == case.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if current_user.username != "admin" and project.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="您不能在别人的项目中创建用例")

    # 排除 schema 中存在但 model 中不存在的字段
    case_data = case.dict(exclude={"project_name"})

    db_case = models.TestCase(**case_data)
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

    check_case_permission(case, current_user)

    if case_in.project_id and case_in.project_id != case.project_id:
        target_project = db.query(models.Project).filter(models.Project.id == case_in.project_id).first()
        if current_user.username != "admin" and target_project.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="不能将用例转移到他人的项目")

    update_data = case_in.dict(exclude_unset=True, exclude={"project_name"})

    for field, value in update_data.items():
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
        check_case_permission(case, current_user)
        # 手动级联删除报告
        db.query(models.TestReport).filter(models.TestReport.test_case_id == case.id).delete()
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

    # [修改] 使用新的字段 is_active_exec 查找“执行用例模型”
    # 去掉了 use_for 查询条件
    llm_config = db.query(models.LLMConfig).filter(
        models.LLMConfig.user_id == current_user.id,
        models.LLMConfig.is_active_exec == True  # <--- 核心修改点
    ).first()

    if not llm_config:
        raise HTTPException(status_code=400, detail="请先在'大模型配置'中激活一个'执行用例模型'")

    # 获取环境变量
    env_vars = {}
    if env_id:
        env_obj = db.query(models.Environment).filter(models.Environment.id == env_id).first()
        if env_obj:
            import json
            try:
                env_vars = json.loads(env_obj.variables)
            except:
                pass

    # 2. 准备配置字典
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
        start_time=datetime.now(),
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    run_midscene_task.delay(new_report.id, llm_env_vars)

    # 手动填充 case name 避免前端显示 null
    return report_to_schema(new_report)


# 6. 获取报告详情
@router.get("/reports/{report_id}", response_model=schemas.TestReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(models.TestReport).filter(models.TestReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return report_to_schema(report)


# 7. 获取报告列表 (支持分页)
@router.get("/reports/", response_model=Dict[str, Any])
def get_reports(
        skip: int = 0,
        limit: int = 20,
        status: Optional[models.TaskStatus] = None,
        case_id: Optional[int] = None,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.TestReport)

    # 显式 Join
    query = query.outerjoin(models.TestCase, models.TestReport.test_case_id == models.TestCase.id)
    query = query.outerjoin(models.Project, models.TestCase.project_id == models.Project.id)

    if current_user.username != "admin":
        query = query.filter(models.Project.owner_id == current_user.id)

    if status:
        query = query.filter(models.TestReport.status == status)
    if case_id:
        query = query.filter(models.TestReport.test_case_id == case_id)

    # 查总数
    total = query.count()

    # 查列表 (预加载 test_case 避免 N+1)
    items = query.order_by(desc(models.TestReport.start_time)) \
        .offset(skip).limit(limit) \
        .options(joinedload(models.TestReport.test_case)) \
        .all()

    # [修复] 转换为 Pydantic 对象列表，解决序列化报错
    result_items = [report_to_schema(item) for item in items]

    return {"total": total, "items": result_items}


# 8. 重跑报告
@router.post("/reports/{report_id}/retry", response_model=schemas.TestReportOut)
def retry_report(
        report_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    old_report = db.query(models.TestReport).filter(models.TestReport.id == report_id).first()
    if not old_report:
        raise HTTPException(status_code=404, detail="Report not found")

    if current_user.username != "admin":
        if old_report.test_case.project.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Permission denied")

    # [修改] 使用 is_active_exec 查找“执行用例模型”
    llm_config = db.query(models.LLMConfig).filter(
        models.LLMConfig.user_id == current_user.id,
        models.LLMConfig.is_active_exec == True  # <--- 核心修改点
    ).first()

    if not llm_config or not llm_config.api_key:
        raise HTTPException(status_code=400, detail="请先在'大模型配置'中激活一个有效的'执行用例模型'")

    llm_env_vars = {
        "api_key": llm_config.api_key,
        "model_name": llm_config.model_name,
        "base_url": llm_config.base_url,
        "provider": llm_config.provider,
        "model_family": llm_config.model_family,
        "custom_env": {}
    }

    new_report = models.TestReport(
        test_case_id=old_report.test_case_id,
        status=models.TaskStatus.PENDING,
        script_content=old_report.test_case.script_content,
        start_time=datetime.now()
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    run_midscene_task.delay(new_report.id, llm_env_vars)

    return report_to_schema(new_report)


# 9. 调试接口
@router.post("/{case_id}/debug", response_model=schemas.TestReportOut)
def debug_test_case(
        case_id: int,
        env_id: Optional[int] = None,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # 复用 run_test_case 的逻辑
    return run_test_case(case_id, env_id, db, current_user)


# 10. 批量运行测试用例
@router.post("/batch-run")
def batch_run_testcases(
    request_data: dict = Body(..., description="请求数据"),
    env_id: Optional[int] = Query(None, description="环境ID"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    case_ids = request_data.get('case_ids', [])
    if not isinstance(case_ids, list):
        raise HTTPException(status_code=400, detail="case_ids 必须是数组")
    """
    批量运行测试用例
    """
    # 创建批次记录
    batch_id = str(uuid.uuid4())
    batch_records = []
    
    # 获取 LLM 配置
    llm_config = db.query(models.LLMConfig).filter(
        models.LLMConfig.user_id == current_user.id,
        models.LLMConfig.is_active_exec == True
    ).first()
    
    if not llm_config:
        raise HTTPException(status_code=400, detail="请先在'大模型配置'中激活一个'执行用例模型'")
    
    # 获取环境变量
    env_vars = {}
    if env_id:
        env_obj = db.query(models.Environment).filter(models.Environment.id == env_id).first()
        if env_obj:
            import json
            try:
                env_vars = json.loads(env_obj.variables)
            except:
                pass
    
    # 准备 LLM 配置
    llm_env_vars = {
        "api_key": llm_config.api_key,
        "model_name": llm_config.model_name or "gpt-4o",
        "base_url": llm_config.base_url or "",
        "provider": llm_config.provider or "openai",
        "model_family": llm_config.model_family,
        "custom_env": env_vars
    }
    
    for case_id in case_ids:
        # 检查用例权限
        case = db.query(models.TestCase).filter(models.TestCase.id == case_id).first()
        if not case:
            continue
        
        check_case_permission(case, current_user)
        
        # 为每个测试用例创建报告记录
        new_report = models.TestReport(
            test_case_id=case_id,
            status=models.TaskStatus.PENDING,
            script_content=case.script_content,
            start_time=datetime.now(),
            batch_id=batch_id
        )
        db.add(new_report)
        batch_records.append(new_report)
    
    db.commit()
    
    # 为每个报告创建 Celery 任务
    for report in batch_records:
        run_midscene_task.delay(report.id, llm_env_vars)
    
    # 调度批量任务完成通知
    # notify_batch_result 任务会检查所有任务是否完成，只有全部完成后才发送飞书通知
    notify_batch_result.delay(batch_id)
    
    return {
        "status": "success",
        "batch_id": batch_id,
        "total_cases": len(batch_records)
    }

