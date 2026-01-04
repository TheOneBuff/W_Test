import json
from datetime import datetime
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import TestCase, Project, TestReport, TaskStatus, User, Environment, PeriodicTask, TaskExecutionLog
from .tasks import run_midscene_task


def exec_periodic_task(task_id: int):
    """
    定时任务的入口函数
    """
    print(f"[Scheduler] Triggering periodic task: {task_id}")
    db: Session = SessionLocal()

    # 1. 先创建日志记录 (状态: running)
    log_entry = TaskExecutionLog(
        periodic_task_id=task_id,
        status="running",
        trigger_time=datetime.now()
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)  # 获取 ID 以便后续更新

    generated_report_ids = []

    try:
        # 2. 获取任务配置
        pt_task = db.query(PeriodicTask).filter(PeriodicTask.id == task_id).first()

        # 检查任务有效性
        if not pt_task:
            raise Exception("Task not found in DB")
        if not pt_task.is_enabled:
            raise Exception("Task is disabled")

        # 3. 确定要执行的用例列表
        target_cases = []
        if pt_task.target_type == 'project' and pt_task.project_id:
            target_cases = db.query(TestCase).filter(TestCase.project_id == pt_task.project_id).all()
        elif pt_task.target_type == 'cases' and pt_task.case_ids:
            try:
                ids = [int(i) for i in pt_task.case_ids.split(',') if i.strip()]
                if ids:
                    target_cases = db.query(TestCase).filter(TestCase.id.in_(ids)).all()
            except ValueError:
                raise Exception("Invalid case_ids format")

        if not target_cases:
            raise Exception("No valid test cases found to run")

        # 4. 准备环境参数
        owner = db.query(User).filter(User.id == pt_task.owner_id).first()
        if not owner or not owner.llm_config or not owner.llm_config.api_key:
            raise Exception("Task owner has no valid LLM/API Key config")

        llm_env_vars = {
            "api_key": owner.llm_config.api_key,
            "model_name": owner.llm_config.model_name or "gpt-4o",
            "base_url": owner.llm_config.base_url,
            "model_family": owner.llm_config.model_family,
            "custom_env": {}
        }

        # 加载指定环境的变量
        if pt_task.env_id:
            env_obj = db.query(Environment).filter(Environment.id == pt_task.env_id).first()
            if env_obj:
                try:
                    llm_env_vars["custom_env"] = json.loads(env_obj.variables)
                except:
                    print(f"Warning: Failed to parse env variables for env_id {pt_task.env_id}")

        # 5. 批量触发 Celery 任务
        print(f"[Scheduler] Task {task_id}: Launching {len(target_cases)} cases...")

        for case in target_cases:
            new_report = TestReport(
                test_case_id=case.id,
                status=TaskStatus.PENDING,
                script_content=case.script_content,
                # 可选：记录是由定时任务触发的
                logs=f"[System] Triggered by Periodic Task: {pt_task.name} (ID: {task_id})"
            )
            db.add(new_report)
            db.commit()
            db.refresh(new_report)

            # 异步执行
            run_midscene_task.delay(new_report.id, llm_env_vars)

            generated_report_ids.append(new_report.id)

        # 6. 更新任务状态和最后运行时间
        pt_task.last_run_time = datetime.now()

        # 更新日志为成功
        log_entry.status = "success"
        log_entry.report_ids = json.dumps(generated_report_ids)
        db.commit()
        print(f"[Scheduler] Task {task_id} completed successfully.")

    except Exception as e:
        print(f"[Scheduler] Error in task {task_id}: {str(e)}")
        # 更新日志为失败
        log_entry.status = "failed"
        log_entry.error_msg = str(e)
        db.commit()

    finally:
        db.close()
