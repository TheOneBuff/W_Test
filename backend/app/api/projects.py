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
        raise HTTPException(status_code=404, detail="项目不存在")

    # 权限检查
    if current_user.username != "admin" and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限")

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
        raise HTTPException(status_code=404, detail="项目不存在")

    if current_user.username != "admin" and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限")

    # --- [新增] 手动级联删除逻辑 ---

    # 1. 查找该项目下所有的用例 ID
    # 注意：这里我们只查 ID 列表，减少内存开销
    case_ids = db.query(models.TestCase.id).filter(models.TestCase.project_id == project_id).all()
    # case_ids 格式类似 [(1,), (2,)]
    case_ids = [cid[0] for cid in case_ids]

    if case_ids:
        # 2. 删除这些用例关联的所有测试报告 (TestReport)
        # 相当于 DELETE FROM test_reports WHERE test_case_id IN (...)
        db.query(models.TestReport).filter(models.TestReport.test_case_id.in_(case_ids)).delete(
            synchronize_session=False)

        # 3. 删除这些用例本身 (TestCase)
        # 相当于 DELETE FROM test_cases WHERE project_id = ...
        db.query(models.TestCase).filter(models.TestCase.project_id == project_id).delete(synchronize_session=False)

    # 4. 最后删除项目
    db.delete(project)

    # 提交事务
    db.commit()

    return {"status": "success"}