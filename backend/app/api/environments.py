from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json
from .. import models, schemas
from ..database import get_db
from .auth import get_current_user

router = APIRouter()


@router.get("/", response_model=List[schemas.EnvOut])
def get_envs(db: Session = Depends(get_db)):
    return db.query(models.Environment).all()


@router.post("/", response_model=schemas.EnvOut)
def create_env(env: schemas.EnvCreate, db: Session = Depends(get_db)):
    # 验证 JSON 格式
    try:
        json.loads(env.variables)
    except:
        raise HTTPException(status_code=400, detail="变量必须是有效的JSON格式")

    db_env = models.Environment(**env.dict())
    db.add(db_env)
    db.commit()
    db.refresh(db_env)
    return db_env


@router.put("/{env_id}", response_model=schemas.EnvOut)
def update_env(env_id: int, env_in: schemas.EnvCreate, db: Session = Depends(get_db)):
    env = db.query(models.Environment).filter(models.Environment.id == env_id).first()
    if not env:
        raise HTTPException(status_code=404, detail="没找到")

    env.name = env_in.name
    env.variables = env_in.variables
    env.description = env_in.description
    db.commit()
    db.refresh(env)
    return env


@router.delete("/{env_id}")
def delete_env(env_id: int, db: Session = Depends(get_db)):
    env = db.query(models.Environment).filter(models.Environment.id == env_id).first()
    if env:
        db.delete(env)
        db.commit()
    return {"status": "success"}
