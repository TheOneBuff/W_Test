from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas
from ..database import get_db
from ..core.security import get_password_hash
from .auth import get_current_user  # 引入权限依赖，确保只有登录用户能操作

router = APIRouter()


# 1. 获取用户列表
@router.get("/", response_model=List[schemas.UserOut])
def read_users(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)  # 必须登录
):
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users


# 2. 创建新用户
@router.post("/", response_model=schemas.UserOut)
def create_user(
        user: schemas.UserCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # 检查用户名是否存在
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="用户已经存在")

    # 哈希密码并存储
    hashed_password = get_password_hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# 3. 删除用户
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
        user_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # (可选) 防止删除自己
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")

    db.delete(user)
    db.commit()
    return None
