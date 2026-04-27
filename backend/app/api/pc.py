from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, Body
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel
import json
import logging

from ..database import get_db
from .. import models, schemas

router = APIRouter()
logger = logging.getLogger(__name__)

EXECUTOR_OFFLINE_TIMEOUT = 60


def update_executor_heartbeat(db: Session, uuid: str):
    executor = db.query(models.Executor).filter(models.Executor.uuid == uuid).first()
    if executor:
        executor.last_heartbeat = datetime.now()
        executor.status = "online"
        db.commit()
        return executor
    return None


@router.post("/executors/register", response_model=schemas.ExecutorOut)
def register_executor(data: schemas.ExecutorRegister, db: Session = Depends(get_db)):
    logger.info(f"[注册请求] 收到执行器注册请求: uuid={data.uuid}, name={data.name}, hostname={data.hostname}, ip={data.ip_address}")
    
    try:
        executor = db.query(models.Executor).filter(
            models.Executor.hostname == data.hostname,
            models.Executor.ip_address == data.ip_address
        ).first()
        
        if executor:
            logger.info(f"[注册请求] 执行器已存在(按hostname+ip匹配)，更新信息: id={executor.id}, old_uuid={executor.uuid}, new_uuid={data.uuid}")
            executor.uuid = data.uuid
            executor.name = data.name
            executor.version = data.version
            executor.os_version = data.os_version
            executor.capabilities = data.capabilities
            executor.status = "online"
            executor.last_heartbeat = datetime.now()
        else:
            logger.info(f"[注册请求] 未找到匹配的执行器(按hostname+ip)，创建新记录")
            executor = models.Executor(
                uuid=data.uuid,
                name=data.name,
                executor_type=data.executor_type or "pc",
                version=data.version,
                ip_address=data.ip_address,
                os_version=data.os_version,
                hostname=data.hostname,
                capabilities=data.capabilities,
                status="online",
                last_heartbeat=datetime.now()
            )
            db.add(executor)
        
        db.commit()
        db.refresh(executor)
        logger.info(f"[注册请求] 成功: executor_id={executor.id}, uuid={executor.uuid}, name={executor.name}")
        
        return executor
    except Exception as e:
        logger.error(f"[注册请求] 失败: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"注册失败: {str(e)}")


@router.get("/executors/", response_model=List[schemas.ExecutorOut])
def list_executors(
    status: Optional[str] = Query(None, description="过滤状态: online/offline/busy"),
    search: Optional[str] = Query(None, description="搜索名称/主机名"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    logger.info(f"[列表请求] 获取执行器列表: status={status}, search={search}, skip={skip}, limit={limit}")
    
    try:
        query = db.query(models.Executor)
        
        timeout = datetime.now() - timedelta(seconds=EXECUTOR_OFFLINE_TIMEOUT)
        
        if status:
            if status == "online":
                query = query.filter(
                    (models.Executor.status == "online") |
                    ((models.Executor.status == "offline") & (models.Executor.last_heartbeat >= timeout))
                )
            elif status == "offline":
                query = query.filter(
                    (models.Executor.status == "offline") &
                    ((models.Executor.last_heartbeat == None) | (models.Executor.last_heartbeat < timeout))
                )
            elif status == "busy":
                query = query.filter(models.Executor.status == "busy")

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (models.Executor.name.ilike(search_pattern)) |
                (models.Executor.hostname.ilike(search_pattern))
            )

        executors = query.order_by(models.Executor.id.desc()).offset(skip).limit(limit).all()
        
        result = []
        for ex in executors:
            is_offline = ex.last_heartbeat and ex.last_heartbeat < timeout
            calculated_status = "offline" if is_offline else ex.status
            if is_offline:
                logger.info(f"[列表] 执行器 {ex.name} 显示离线: last_heartbeat={ex.last_heartbeat}, timeout={timeout}")
            
            ex_dict = {
                "id": ex.id,
                "uuid": ex.uuid,
                "name": ex.name,
                "executor_type": ex.executor_type,
                "version": ex.version,
                "ip_address": ex.ip_address,
                "os_version": ex.os_version,
                "hostname": ex.hostname,
                "status": calculated_status,
                "last_heartbeat": ex.last_heartbeat,
                "capabilities": ex.capabilities,
                "is_active": ex.is_active,
                "create_time": ex.create_time
            }
            result.append(ex_dict)
        
        logger.info(f"[列表请求] 返回 {len(result)} 条记录")
        return result
    except Exception as e:
        logger.error(f"[列表请求] 失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/executors/{executor_id}", response_model=schemas.ExecutorOut)
def get_executor(executor_id: int, db: Session = Depends(get_db)):
    executor = db.query(models.Executor).filter(models.Executor.id == executor_id).first()
    if not executor:
        raise HTTPException(404, "Executor not found")
    
    timeout = datetime.now() - timedelta(seconds=EXECUTOR_OFFLINE_TIMEOUT)
    status = "offline" if executor.last_heartbeat and executor.last_heartbeat < timeout else executor.status
    
    return schemas.ExecutorOut(
        id=executor.id,
        uuid=executor.uuid,
        name=executor.name,
        executor_type=executor.executor_type,
        version=executor.version,
        ip_address=executor.ip_address,
        os_version=executor.os_version,
        hostname=executor.hostname,
        status=status,
        last_heartbeat=executor.last_heartbeat,
        capabilities=executor.capabilities,
        is_active=executor.is_active,
        create_time=executor.create_time
    )


@router.patch("/executors/{executor_id}", response_model=schemas.ExecutorOut)
def update_executor(executor_id: int, data: schemas.ExecutorUpdate, db: Session = Depends(get_db)):
    executor = db.query(models.Executor).filter(models.Executor.id == executor_id).first()
    if not executor:
        raise HTTPException(404, "Executor not found")
    
    if data.name is not None:
        executor.name = data.name
    if data.is_active is not None:
        executor.is_active = data.is_active
    
    executor.update_time = datetime.now()
    db.commit()
    db.refresh(executor)
    return executor


@router.delete("/executors/{executor_id}")
def delete_executor(executor_id: int, db: Session = Depends(get_db)):
    executor = db.query(models.Executor).filter(models.Executor.id == executor_id).first()
    if not executor:
        raise HTTPException(404, "Executor not found")
    
    db.delete(executor)
    db.commit()
    return {"message": "Executor deleted"}


@router.post("/executors/{executor_id}/wake")
def wake_executor(executor_id: int, db: Session = Depends(get_db)):
    executor = db.query(models.Executor).filter(models.Executor.id == executor_id).first()
    if not executor:
        raise HTTPException(404, "Executor not found")
    
    return {"message": "Wake signal sent", "executor_uuid": executor.uuid}


class ExecutorStatusRequest(BaseModel):
    uuid: str
    status: str


@router.post("/executors/status")
def report_executor_status(data: ExecutorStatusRequest, db: Session = Depends(get_db)):
    logger.info(f"[状态上报] 收到执行器状态上报: uuid={data.uuid}, status={data.status}")
    
    try:
        executor = db.query(models.Executor).filter(models.Executor.uuid == data.uuid).first()
        if executor:
            executor.status = data.status
            executor.last_heartbeat = datetime.now()
            db.commit()
            logger.info(f"[状态上报] 执行器 {executor.name} 状态已更新为 {data.status}")
            return {"success": True, "message": "Status updated"}
        
        logger.warning(f"[状态上报] 未找到执行器: uuid={data.uuid}")
        return {"success": False, "message": "Executor not found"}
    except Exception as e:
        logger.error(f"[状态上报] 失败: {str(e)}")
        return {"success": False, "message": str(e)}


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, uuid: str):
        await websocket.accept()
        self.active_connections[uuid] = websocket

    def disconnect(self, uuid: str):
        if uuid in self.active_connections:
            del self.active_connections[uuid]

    async def send_personal_message(self, message: str, uuid: str):
        if uuid in self.active_connections:
            await self.active_connections[uuid].send_text(message)


manager = ConnectionManager()


@router.websocket("/ws/executor")
async def executor_websocket(websocket: WebSocket, db: Session = Depends(get_db)):
    uuid = None
    try:
        await websocket.accept()
        
        while True:
            data = await websocket.receive_text()
            logger.info(f"[WebSocket] 收到原始数据: {data}")
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")
                logger.info(f"[WebSocket] 收到消息: {msg_type}, data={msg}")
                if msg_type == "register":
                    uuid = msg.get("uuid")
                    logger.info(f"[WebSocket] 收到注册消息: uuid={uuid}")
                    await manager.connect(websocket, uuid)
                    logger.info(f"[WebSocket] 连接已建立: uuid={uuid}")
                    
                    update_executor_heartbeat(db, uuid)
                    
                    await websocket.send_text(json.dumps({
                        "type": "registered",
                        "uuid": uuid,
                        "status": "online"
                    }))
                    
                elif msg_type == "heartbeat":
                    uuid = msg.get("uuid")
                    logger.info(f"[WebSocket] 收到心跳: uuid={uuid}, data={msg}")
                    update_executor_heartbeat(db, uuid)
                    logger.info(f"[WebSocket] heartbeat_ack 已发送")
                    await websocket.send_text(json.dumps({
                        "type": "heartbeat_ack",
                        "timestamp": datetime.now().isoformat()
                    }))
                    
                elif msg_type == "status_update":
                    executor_uuid = msg.get("uuid")
                    status = msg.get("status", "online")
                    update_executor_heartbeat(db, executor_uuid)
                    
                    executor = db.query(models.Executor).filter(
                        models.Executor.uuid == executor_uuid
                    ).first()
                    if executor:
                        executor.status = status
                        db.commit()
                        
                elif msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON"
                }))
                
    except WebSocketDisconnect:
        if uuid:
            manager.disconnect(uuid)
            update_executor_heartbeat(db, uuid)
    except Exception as e:
        if uuid:
            manager.disconnect(uuid)

@router.post("/executors/heartbeat")
def executor_heartbeat(uuid: str, db: Session = Depends(get_db)):
    logger.info(f"[HTTP] 收到心跳: uuid={uuid}")
    executor = update_executor_heartbeat(db, uuid)
    if executor:
        return {"status": "ok", "uuid": uuid}
    return {"status": "error", "message": "executor not found"}


@router.post("/executors/report")
def executor_report(data: dict, db: Session = Depends(get_db)):
    report_id = data.get('report_id')
    status = data.get('status')
    logs = data.get('logs', '')
    report_html = data.get('report_html', '')
    error_info = data.get('error_info', '')
    logger.info(f"[HTTP] 收到报告: report_id={report_id}, status={status}")
    
    report = db.query(models.TestReport).filter(models.TestReport.id == report_id).first()
    if report:
        report.status = models.TaskStatus.SUCCESS if status == 'success' else models.TaskStatus.FAILED
        report.end_time = datetime.now()
        report.logs = logs
        if report_html:
            report.report_path = report_html
        
        executor = db.query(models.Executor).filter(models.Executor.id == report.executor_id).first()
        if executor:
            executor.status = "online"
        
        db.commit()
        logger.info(f"[HTTP] 报告已更新: report_id={report_id}, status={report.status}")
    
    return {"status": "ok", "report_id": report_id}


@router.get("/executors/{uuid}/tasks/pending")
def get_pending_tasks(uuid: str, db: Session = Depends(get_db)):
    executor = db.query(models.Executor).filter(models.Executor.uuid == uuid).first()
    if not executor:
        return []
    tasks = db.query(models.TestReport).filter(
        models.TestReport.executor_id == executor.id,
        models.TestReport.status == 'pending'
    ).all()
    result = []
    for t in tasks:
        case = db.query(models.TestCase).filter(models.TestCase.id == t.test_case_id).first()
        user_id = case.project.owner_id if case and case.project else 1
        llm_env_vars = _get_llm_env_vars(db, user_id)
        result.append({
            "id": t.id,
            "name": case.name if case else "未知",
            "script": case.script_content if case else "",
            "script_type": case.script_type if case else "yaml",
            "llm_config": llm_env_vars
        })
    return result


@router.post("/executors/status")
def executor_status(data: dict, db: Session = Depends(get_db)):
    report_id = data.get('report_id')
    status = data.get('status')
    logs = data.get('logs', '')
    logger.info(f"[HTTP] 收到状态: report_id={report_id}, status={status}")
    return {"status": "ok"}


@router.post("/executors/log")
def executor_log(data: dict, db: Session = Depends(get_db)):
    report_id = data.get('report_id')
    content = data.get('content', '')
    logger.info(f"[HTTP] 收到日志: report_id={report_id}")
    return {"status": "ok"}


class TaskDispatchRequest(BaseModel):
    case_id: int
    executor_id: int
    llm_config_id: Optional[int] = None


class TaskDispatchResponse(BaseModel):
    id: int
    status: str
    executor_name: Optional[str] = None


def _get_llm_env_vars(db: Session, user_id: int, llm_config_id: Optional[int] = None) -> dict:
    if llm_config_id:
        llm = db.query(models.LLMConfig).filter(
            models.LLMConfig.id == llm_config_id,
            models.LLMConfig.user_id == user_id
        ).first()
    else:
        llm = db.query(models.LLMConfig).filter(
            models.LLMConfig.user_id == user_id,
            models.LLMConfig.is_active_exec == True
        ).first()
    
    if not llm:
        return {}
    
    return {
        "api_key": llm.api_key or "",
        "model_name": llm.model_name or "gpt-4o",
        "base_url": llm.base_url or "",
        "provider": llm.provider or "openai",
        "model_family": llm.model_family,
    }


@router.post("/tasks/dispatch", response_model=schemas.TestReportOut)
def dispatch_pc_task(
    data: TaskDispatchRequest,
    db: Session = Depends(get_db)
):
    case = db.query(models.TestCase).filter(models.TestCase.id == data.case_id).first()
    if not case:
        raise HTTPException(404, "Test case not found")
    
    executor = db.query(models.Executor).filter(models.Executor.id == data.executor_id).first()
    if not executor:
        raise HTTPException(404, "Executor not found")
    
    if not executor.is_active:
        raise HTTPException(400, "Executor is not active")
    
    timeout = datetime.now() - timedelta(seconds=EXECUTOR_OFFLINE_TIMEOUT)
    if executor.last_heartbeat and executor.last_heartbeat < timeout:
        raise HTTPException(400, "Executor is offline")
    
    logger.info(f"[任务下发] case_id={data.case_id}, executor_id={data.executor_id}, executor_name={executor.name}")
    
    # 获取 LLM 配置
    user_id = case.project.owner_id if case.project else 1
    llm_env_vars = _get_llm_env_vars(db, user_id, data.llm_config_id)
    logger.info(f"[任务下发] LLM配置: {llm_env_vars.get('model_name', '未配置')}")
    
    new_report = models.TestReport(
        test_case_id=data.case_id,
        executor_id=data.executor_id,
        status=models.TaskStatus.PENDING,
        script_content=case.script_content
    )
    db.add(new_report)
    logger.info(f"[任务下发] TestReport 已写入, start_time={new_report.start_time}")
    
    executor.status = "busy"
    executor.last_heartbeat = datetime.now()
    
    db.commit()
    db.refresh(new_report)
    
    return schemas.TestReportOut(
        id=new_report.id,
        status=new_report.status,
        start_time=new_report.start_time,
        end_time=new_report.end_time,
        report_path=new_report.report_path,
        logs=new_report.logs,
        test_case_id=new_report.test_case_id,
        test_case_name=case.name
    )


@router.get("/tasks/{task_id}/status")
def get_task_status(task_id: int, db: Session = Depends(get_db)):
    report = db.query(models.TestReport).filter(models.TestReport.id == task_id).first()
    if not report:
        raise HTTPException(404, "Task not found")
    
    return {
        "id": report.id,
        "status": report.status,
        "start_time": report.start_time,
        "end_time": report.end_time
    }
