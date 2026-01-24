from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas
from typing import List

router = APIRouter()


# 获取所有模型配置
@router.get("/", response_model=List[schemas.LLMConfig])
def get_llm_configs(db: Session = Depends(get_db)):
    return db.query(models.LLMConfig).all()


# 创建/更新模型配置 (通用CRUD)
@router.post("/", response_model=schemas.LLMConfig)
def create_llm_config(config: schemas.LLMConfigCreate, db: Session = Depends(get_db)):
    db_config = models.LLMConfig(**config.dict())
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config


# ✨ 核心接口：设置某个模型为特定用途的激活模型
@router.post("/{config_id}/activate")
def activate_model(
        config_id: int,
        purpose: str,  # 参数: 'chat', 'gen', 'exec'
        db: Session = Depends(get_db)
):
    # 1. 验证 purpose 合法性
    allowed_purposes = {
        'chat': 'is_active_chat',
        'gen': 'is_active_gen',
        'exec': 'is_active_exec'
    }
    if purpose not in allowed_purposes:
        raise HTTPException(400, "Invalid purpose. Use 'chat', 'gen', or 'exec'")

    target_field = allowed_purposes[purpose]

    # 2. 事务处理：先把所有同类模型的该字段设为 False
    #    这里利用 update 语句批量更新，效率更高
    db.query(models.LLMConfig).update({target_field: False})

    # 3. 把指定的模型设为 True
    model = db.query(models.LLMConfig).filter(models.LLMConfig.id == config_id).first()
    if not model:
        raise HTTPException(404, "Model config not found")

    setattr(model, target_field, True)

    db.commit()
    return {"status": "ok", "message": f"Model {model.name} is now active for {purpose}"}


# 删除模型
@router.delete("/{config_id}")
def delete_llm_config(config_id: int, db: Session = Depends(get_db)):
    db.query(models.LLMConfig).filter(models.LLMConfig.id == config_id).delete()
    db.commit()
    return {"status": "ok"}