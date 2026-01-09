from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from .auth import get_current_user

router = APIRouter()


def get_or_create_config(db: Session, user_id: int):
    config = db.query(models.LLMConfig).filter(models.LLMConfig.user_id == user_id).first()
    if not config:
        config = models.LLMConfig(user_id=user_id)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.get("/", response_model=schemas.LLMConfigOut)
def get_config(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    config = get_or_create_config(db, current_user.id)

    # 手动处理掩码，不直接返回真实 Key
    masked_key = ""
    if config.api_key:
        if len(config.api_key) > 8:
            masked_key = config.api_key[:3] + "****" + config.api_key[-4:]
        else:
            masked_key = "******"

    return schemas.LLMConfigOut(
        provider=config.provider,
        model_name=config.model_name,
        base_url=config.base_url,
        api_key_masked=masked_key,
        model_family=config.model_family
    )


@router.put("/", response_model=schemas.LLMConfigOut)
def update_config(
        data: schemas.LLMConfigUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    config = get_or_create_config(db, current_user.id)

    config.provider = data.provider
    config.model_name = data.model_name
    config.base_url = data.base_url
    config.model_family = data.model_family
    config.memo = data.memo
    # 关键逻辑：只有当用户输入了新的 Key (不包含星号) 时才更新
    # 简单的判断：如果包含 **** 则认为是掩码，不更新
    if data.api_key and "****" not in data.api_key:
        config.api_key = data.api_key

    db.commit()
    db.refresh(config)

    # 构造返回
    masked_key = data.api_key if data.api_key and "****" in data.api_key else (
        config.api_key[:3] + "****" if config.api_key else "")

    return schemas.LLMConfigOut(
        provider=config.provider,
        model_name=config.model_name,
        base_url=config.base_url,
        api_key_masked=masked_key,
        model_family=config.model_family
    )
