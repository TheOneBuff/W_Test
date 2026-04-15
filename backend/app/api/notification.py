from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas
from ..database import get_db
from .auth import get_current_user
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import requests
from datetime import datetime

router = APIRouter()


def send_feishu_webhook(webhook_url: str, message: str) -> bool:
    try:
        payload = {"msg_type": "text", "content": {"text": message}}
        resp = requests.post(webhook_url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def send_feishu_notification(webhook_url: str, summary: str, details: str) -> bool:
    message = f"{summary}\n{details}"
    return send_feishu_webhook(webhook_url, message)


def send_weixin_webhook(webhook_url: str, message: str) -> bool:
    try:
        payload = {"msgtype": "text", "text": {"content": message}}
        resp = requests.post(webhook_url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def send_email(smtp_host: str, smtp_port: int, username: str, password: str,
            from_addr: str, to_addrs: List[str], subject: str, message: str) -> bool:
    try:
        msg = MIMEMultipart()
        msg['From'] = from_addr
        msg['To'] = ', '.join(to_addrs)
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'html', 'utf-8'))

        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(username, password)
        server.sendmail(from_addr, to_addrs, msg.as_string())
        server.quit()
        return True
    except Exception:
        return False


def send_notification(config: models.NotificationConfig, message: str, subject: str = "测试通知") -> bool:
    cfg = config.config_json or {}
    channel = config.channel

    if channel == "feishu":
        webhook_url = cfg.get("webhook_url")
        if webhook_url:
            return send_feishu_webhook(webhook_url, message)
    elif channel == "weixin":
        webhook_url = cfg.get("webhook_url")
        if webhook_url:
            return send_weixin_webhook(webhook_url, message)
    elif channel == "email":
        smtp_host = cfg.get("smtp_host", "smtp.qq.com")
        smtp_port = cfg.get("smtp_port", 587)
        username = cfg.get("username")
        password = cfg.get("password")
        from_addr = cfg.get("from_addr")
        to_addrs = cfg.get("to_addrs", [])

        if username and password and from_addr and to_addrs:
            return send_email(smtp_host, smtp_port, username, password, from_addr, to_addrs, subject, message)

    return False


@router.get("/", response_model=List[schemas.NotificationConfigOut])
def get_notification_configs(db: Session = Depends(get_db)):
    return db.query(models.NotificationConfig).order_by(models.NotificationConfig.created_at.desc()).all()


@router.post("/", response_model=schemas.NotificationConfigOut)
def create_notification_config(
        config: schemas.NotificationConfigCreate,
        db: Session = Depends(get_db)
):
    if config.is_default:
        db.query(models.NotificationConfig).update({"is_default": False})

    db_config = models.NotificationConfig(**config.dict())
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config


@router.put("/{config_id}", response_model=schemas.NotificationConfigOut)
def update_notification_config(
        config_id: int,
        config_in: schemas.NotificationConfigUpdate,
        db: Session = Depends(get_db)
):
    db_config = db.query(models.NotificationConfig).filter(
        models.NotificationConfig.id == config_id
    ).first()

    if not db_config:
        raise HTTPException(status_code=404, detail="Config not found")

    if config_in.is_default and not db_config.is_default:
        db.query(models.NotificationConfig).filter(
            models.NotificationConfig.id != config_id
        ).update({"is_default": False})

    update_data = config_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_config, field, value)

    db.commit()
    db.refresh(db_config)
    return db_config


@router.delete("/{config_id}")
def delete_notification_config(
        config_id: int,
        db: Session = Depends(get_db)
):
    db_config = db.query(models.NotificationConfig).filter(
        models.NotificationConfig.id == config_id
    ).first()

    if not db_config:
        raise HTTPException(status_code=404, detail="Config not found")

    db.delete(db_config)
    db.commit()
    return {"status": "ok"}


@router.post("/test", response_model=schemas.NotificationTestResponse)
def test_notification(
        test_req: schemas.NotificationTestRequest,
        db: Session = Depends(get_db)
):
    db_config = db.query(models.NotificationConfig).filter(
        models.NotificationConfig.id == test_req.config_id
    ).first()

    if not db_config:
        raise HTTPException(status_code=404, detail="Config not found")

    if not db_config.is_enabled:
        return schemas.NotificationTestResponse(
            success=False,
            message="通知渠道未启用"
        )

    message = test_req.test_message or "这是一条测试通知"
    success = send_notification(db_config, message, "通知配置测试")

    return schemas.NotificationTestResponse(
        success=success,
        message="发送成功" if success else "发送失败，请检查配置"
    )