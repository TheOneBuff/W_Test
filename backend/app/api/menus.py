from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas
from ..database import get_db
from .auth import get_current_user

router = APIRouter()


# 辅助函数：构建树形结构
def build_menu_tree(menus, parent_id=None):
    tree = []
    for menu in menus:
        if menu.parent_id == parent_id:
            # 递归查找子节点
            children = build_menu_tree(menus, menu.id)
            # 使用 Pydantic 模型转换，如果有子节点则赋值
            menu_dict = schemas.MenuOut.from_orm(menu)
            if children:
                menu_dict.children = children
            tree.append(menu_dict)
    return tree


@router.get("/", response_model=List[schemas.MenuOut])
def get_menus(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # 1. 查询所有菜单，按 sort 排序
    all_menus = db.query(models.Menu).filter(models.Menu.is_hidden == False).order_by(models.Menu.sort).all()

    # 2. 如果是 Admin，返回所有；如果是普通用户，这里可以加权限过滤逻辑
    # 目前简化为：登录即返回所有菜单

    # 3. 组装成树形结构
    return build_menu_tree(all_menus)


@router.post("/", response_model=schemas.MenuOut)
def create_menu(
        menu: schemas.MenuCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    db_menu = models.Menu(**menu.dict())
    db.add(db_menu)
    db.commit()
    db.refresh(db_menu)
    return db_menu


@router.delete("/{menu_id}")
def delete_menu(menu_id: int, db: Session = Depends(get_db)):
    menu = db.query(models.Menu).filter(models.Menu.id == menu_id).first()
    if menu:
        db.delete(menu)
        db.commit()
    return {"status": "success"}
