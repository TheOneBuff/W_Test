from typing import List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from .auth import get_current_user
from ..core.scheduler import scheduler
from ..jobs import exec_periodic_task

router = APIRouter()


@router.post("/", response_model=schemas.PeriodicTaskOut)
def create_periodic_task(
        task: schemas.PeriodicTaskCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # 1. 存入数据库
    db_task = models.PeriodicTask(**task.dict(), owner_id=current_user.id)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    # 2. 注册到 APScheduler
    # 使用 cron 触发器
    # 假设前端传来的 cron_expr 格式为 "min hour day month day_of_week" (空格分隔)
    # 例如 "30 2 * * *" -> 每天 2:30 执行

    try:
        cron_parts = task.cron_expr.split()
        if len(cron_parts) != 5:
            raise Exception("Invalid cron format")

        scheduler.add_job(
            exec_periodic_task,
            'cron',
            args=[db_task.id],
            id=str(db_task.id),
            minute=cron_parts[0],
            hour=cron_parts[1],
            day=cron_parts[2],
            month=cron_parts[3],
            day_of_week=cron_parts[4],
            replace_existing=True
        )
    except Exception as e:
        # 如果调度注册失败，回滚数据库
        db.delete(db_task)
        db.commit()
        raise HTTPException(status_code=400, detail=f"Cron 表达式错误: {str(e)}")

    return db_task


@router.delete("/{task_id}")
def delete_periodic_task(task_id: int, db: Session = Depends(get_db)):
    # 1. 删数据库
    db_task = db.query(models.PeriodicTask).filter(models.PeriodicTask.id == task_id).first()
    if db_task:
        db.delete(db_task)
        db.commit()

    # 2. 删调度器
    if scheduler.get_job(str(task_id)):
        scheduler.remove_job(str(task_id))

    return {"status": "success"}

# 还需要 update 接口 (略)，记得 update 数据库的同时要 scheduler.reschedule_job
@router.get("/", response_model=List[schemas.PeriodicTaskOut])
def get_periodic_tasks(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # 简单处理：返回所有任务（或者只返回自己的）
    return db.query(models.PeriodicTask).filter(models.PeriodicTask.owner_id == current_user.id).all()


@router.post("/{task_id}/run")
def run_periodic_task_now(
        task_id: int,
        background_tasks: BackgroundTasks,  # 使用 FastAPI 的后台任务
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # 1. 检查任务是否存在且有权操作
    task = db.query(models.PeriodicTask).filter(models.PeriodicTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 2. 立即触发执行函数
    # 注意：这里我们使用 BackgroundTasks 在响应返回后异步执行，
    # 避免阻塞 HTTP 请求。也可以用 Celery task 来包一层。
    # 因为 exec_periodic_task 内部也是触发 Celery 任务，所以这里很快。
    background_tasks.add_task(exec_periodic_task, task_id)

    return {"status": "triggered"}


@router.get("/{task_id}/logs", response_model=List[schemas.TaskLogOut])
def get_task_logs(
    task_id: int,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    return db.query(models.TaskExecutionLog)\
             .filter(models.TaskExecutionLog.periodic_task_id == task_id)\
             .order_by(models.TaskExecutionLog.trigger_time.desc())\
             .limit(limit)\
             .all()


@router.put("/{task_id}", response_model=schemas.PeriodicTaskOut)
def update_periodic_task(
        task_id: int,
        task_in: schemas.PeriodicTaskCreate,  # 复用 Create Schema
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # 1. 查找并校验权限
    db_task = db.query(models.PeriodicTask).filter(models.PeriodicTask.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    if db_task.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 2. 更新数据库字段
    db_task.name = task_in.name
    db_task.cron_expr = task_in.cron_expr
    db_task.target_type = task_in.target_type
    db_task.project_id = task_in.project_id
    db_task.case_ids = task_in.case_ids
    db_task.env_id = task_in.env_id
    db_task.is_enabled = task_in.is_enabled

    db.commit()
    db.refresh(db_task)

    # 3. 更新调度器 (Reschedule)
    try:
        cron_parts = task_in.cron_expr.split()
        if len(cron_parts) != 5:
            raise Exception("Invalid cron format")

        # 无论之前是否存在 Job，都尝试重新添加或更新
        # 如果 Job 已存在，replace_existing=True 会更新它
        # 如果 Job 之前被删了，add_job 会新建它
        # 只有当 is_enabled=True 时才调度
        if db_task.is_enabled:
            scheduler.add_job(
                exec_periodic_task,
                'cron',
                args=[db_task.id],
                id=str(db_task.id),
                minute=cron_parts[0],
                hour=cron_parts[1],
                day=cron_parts[2],
                month=cron_parts[3],
                day_of_week=cron_parts[4],
                replace_existing=True
            )
        else:
            # 如果禁用了，移除 Job
            if scheduler.get_job(str(db_task.id)):
                scheduler.remove_job(str(db_task.id))

    except Exception as e:
        print(f"Scheduler update failed: {e}")
        # 这里可以选择回滚或者仅记录日志

    return db_task
