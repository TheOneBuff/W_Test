from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas
from ..database import get_db
from .auth import get_current_user

router = APIRouter()


# 1. 获取项目列表
@router.get("/", response_model=List[schemas.ProjectOut])
def get_projects(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # 如果是 admin，查看所有项目
    if current_user.username == "admin":
        return db.query(models.Project).all()
    # 否则只查看自己的项目
    return db.query(models.Project).filter(models.Project.owner_id == current_user.id).all()


# 2. 创建项目
@router.post("/", response_model=schemas.ProjectOut)
def create_project(
        project: schemas.ProjectCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    db_project = models.Project(**project.dict(), owner_id=current_user.id)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


# 3. 更新项目
@router.put("/{project_id}", response_model=schemas.ProjectOut)
def update_project(
        project_id: int,
        project_in: schemas.ProjectCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 权限检查
    if current_user.username != "admin" and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    project.name = project_in.name
    project.description = project_in.description
    db.commit()
    db.refresh(project)
    return project


# 4. 删除项目
@router.delete("/{project_id}")
def delete_project(
        project_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.username != "admin" and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    db.delete(project)
    db.commit()
    return {"status": "success"}
