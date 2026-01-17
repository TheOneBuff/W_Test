from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas
from ..database import get_db
from .auth import get_current_user

router = APIRouter()


# 1. 获取配置列表 (返回 List)
@router.get("/", response_model=List[schemas.LLMConfigOut])
def get_configs(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    configs = db.query(models.LLMConfig).filter(models.LLMConfig.user_id == current_user.id).all()

    # 手动处理掩码 (虽然 Schema 里可能会处理，但在这里显式处理更安全)
    for c in configs:
        if c.api_key:
            if len(c.api_key) > 8:
                c.api_key_masked = c.api_key[:3] + "****" + c.api_key[-4:]
            else:
                c.api_key_masked = "******"
        else:
            c.api_key_masked = ""

    return configs


# 2. 创建新配置
@router.post("/", response_model=schemas.LLMConfigOut)
def create_config(
        config: schemas.LLMConfigCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # 检查用户是否已有配置
    count = db.query(models.LLMConfig).filter(models.LLMConfig.user_id == current_user.id).count()

    # 如果是第一个配置，强制激活；否则沿用前端传来的 is_active
    is_active = True if count == 0 else config.is_active

    if is_active:
        # 如果新配置要激活，先停用其他所有
        db.query(models.LLMConfig).filter(models.LLMConfig.user_id == current_user.id).update({"is_active": False})

    db_config = models.LLMConfig(**config.dict(), user_id=current_user.id)
    db_config.is_active = is_active

    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config


# 3. 更新配置
@router.put("/{config_id}", response_model=schemas.LLMConfigOut)
def update_config(
        config_id: int,
        data: schemas.LLMConfigUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    config = db.query(models.LLMConfig).filter(models.LLMConfig.id == config_id).first()
    if not config or config.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Config not found")

    # 互斥激活逻辑: 如果要把当前配置激活，则停用其他
    if data.is_active and not config.is_active:
        db.query(models.LLMConfig).filter(models.LLMConfig.user_id == current_user.id).update({"is_active": False})

    # 更新字段
    for k, v in data.dict(exclude_unset=True).items():
        # 如果 key 是 api_key 且包含掩码，说明用户没改密码，跳过更新
        if k == "api_key" and v and "****" in v:
            continue
        setattr(config, k, v)

    db.commit()
    db.refresh(config)

    # 返回时带上掩码
    if config.api_key:
        if len(config.api_key) > 8:
            config.api_key_masked = config.api_key[:3] + "****" + config.api_key[-4:]
        else:
            config.api_key_masked = "******"

    return config


# 4. 删除配置
@router.delete("/{config_id}")
def delete_config(
        config_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    config = db.query(models.LLMConfig).filter(models.LLMConfig.id == config_id).first()
    if config and config.user_id == current_user.id:
        db.delete(config)
        db.commit()
    return {"status": "success"}


# 5. 激活配置 (快捷接口)
# midwhp/backend/app/api/llm_config.py

@router.post("/{config_id}/activate")
def activate_config(
        config_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # 1. 找到要激活的目标配置
    target_config = db.query(models.LLMConfig).filter(
        models.LLMConfig.id == config_id,
        models.LLMConfig.user_id == current_user.id
    ).first()

    if not target_config:
        raise HTTPException(status_code=404, detail="Config not found")

    # 2. [关键修改] 先把“同类型”的其他配置设为 False
    # 比如：如果我要激活一个 Embedding 模型，我只把其他的 Embedding 模型关掉
    # 不会影响已经激活的 Generation 模型
    db.query(models.LLMConfig).filter(
        models.LLMConfig.user_id == current_user.id,
        models.LLMConfig.use_for == target_config.use_for,  # <--- 限定用途
        models.LLMConfig.is_active == True
    ).update({"is_active": False})

    # 3. 激活当前目标
    target_config.is_active = True
    db.commit()

    return {"status": "success", "msg": f"Activated {target_config.use_for} model"}


# [新增] 获取当前激活的配置
@router.get("/active")
def get_active_config(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    config = db.query(models.LLMConfig).filter(
        models.LLMConfig.user_id == current_user.id,
        models.LLMConfig.is_active == True
    ).first()

    if not config:
        return {}  # 或者返回 None，前端做判空处理

    return config