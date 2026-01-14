import json
from datetime import datetime
from sqlalchemy.orm import Session
from .database import SessionLocal
# 引入 LLMConfig
from .models import TestCase, TestReport, TaskStatus, User, Environment, PeriodicTask, TaskExecutionLog, \
    LLMConfig
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
    db.refresh(log_entry)

    generated_report_ids = []

    try:
        # 2. 获取任务配置
        pt_task = db.query(PeriodicTask).filter(PeriodicTask.id == task_id).first()

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

        # 4. 准备环境参数 (修正：查找 Owner 的激活配置)
        # ----------------------------------------------------
        owner = db.query(User).filter(User.id == pt_task.owner_id).first()
        if not owner:
            raise Exception("Task owner not found")

        # 查找该用户激活的 LLM 配置
        llm_config = db.query(LLMConfig).filter(
            LLMConfig.user_id == owner.id,
            LLMConfig.is_active == True
        ).first()

        if not llm_config or not llm_config.api_key:
            raise Exception(f"Task owner ({owner.username}) has no active LLM config")
        # ----------------------------------------------------

        llm_env_vars = {
            "api_key": llm_config.api_key,
            "model_name": llm_config.model_name or "gpt-4o",
            "base_url": llm_config.base_url,
            "model_family": llm_config.model_family,
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
                status=TaskStatus.PENDING,  # 兼容
                script_content=case.script_content,
                logs=f"[System] Triggered by Periodic Task: {pt_task.name} (ID: {task_id})",
                start_time=datetime.now()
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
