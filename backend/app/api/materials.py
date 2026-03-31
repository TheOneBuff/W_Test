from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from datetime import datetime
from .. import models, schemas
from ..database import get_db
from .auth import get_current_user

router = APIRouter()

# 上传目录
UPLOAD_DIR = "/data/uploads"

# 确保上传目录存在
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/", response_model=schemas.MaterialOut)
async def upload_material(
    file: UploadFile = File(...),
    name: str = Form(...),
    project_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 验证文件类型
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只支持图片上传")
    
    # 生成唯一文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # 保存文件
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # 计算文件大小
    file_size = len(content)
    
    # 创建素材记录
    db_material = models.Material(
        name=name,
        file_path=file_path,
        file_type=file.content_type,
        file_size=file_size,
        project_id=project_id
    )
    
    db.add(db_material)
    db.commit()
    db.refresh(db_material)
    
    return db_material


@router.get("/", response_model=List[schemas.MaterialOut])
def get_materials(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.Material)
    
    if project_id:
        query = query.filter(models.Material.project_id == project_id)
    
    return query.order_by(models.Material.create_time.desc()).all()


@router.delete("/{material_id}")
def delete_material(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    material = db.query(models.Material).filter(models.Material.id == material_id).first()
    
    if not material:
        raise HTTPException(status_code=404, detail="素材不存在")
    
    # 删除文件
    if os.path.exists(material.file_path):
        os.remove(material.file_path)
    
    # 删除记录
    db.delete(material)
    db.commit()
    
    return {"status": "success"}
