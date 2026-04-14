from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas
from typing import List
from .auth import get_current_user
import requests

router = APIRouter()


def test_openai_connection(base_url: str, api_key: str, model_name: str) -> tuple:
    """测试 OpenAI 兼容 API 连接"""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 10
        }
        resp = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            json=payload,
            headers=headers,
            timeout=30
        )
        if resp.status_code == 200:
            return True, "连接成功"
        else:
            return False, f"请求失败: {resp.status_code} - {resp.text[:100]}"
    except requests.exceptions.Timeout:
        return False, "请求超时"
    except requests.exceptions.ConnectionError:
        return False, "无法连接到服务器"
    except Exception as e:
        return False, f"错误: {str(e)}"


# 获取所有模型配置
@router.get("/", response_model=List[schemas.LLMConfig])
def get_llm_configs(db: Session = Depends(get_db)):
    return db.query(models.LLMConfig).all()


# 创建/更新模型配置 (通用CRUD)
@router.post("/", response_model=schemas.LLMConfig)
def create_llm_config(config: schemas.LLMConfigCreate, db: Session = Depends(get_db),
                      current_user: models.User = Depends(get_current_user)):
    db_config = models.LLMConfig(
        **config.dict(),
        user_id=current_user.id
    )
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
def delete_llm_config(
        config_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)  # 添加依赖
):
    # 查询时同时校验 id 和 user_id
    config = db.query(models.LLMConfig).filter(
        models.LLMConfig.id == config_id,
        models.LLMConfig.user_id == current_user.id  # 确保只能删自己的
    ).first()

    if not config:
        raise HTTPException(status_code=404, detail="Config not found or permission denied")

    db.delete(config)
    db.commit()
    return {"status": "ok"}


# backend/app/api/llm.py

# ... (其他导入保持不变)
from .. import models, schemas
from .auth import get_current_user  # 确保引入了权限验证



# 3. 更新配置
@router.put("/{config_id}", response_model=schemas.LLMConfig)
def update_llm_config(
        config_id: int,
        config_in: schemas.LLMConfigUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # 1. 查询配置是否存在
    db_config = db.query(models.LLMConfig).filter(models.LLMConfig.id == config_id).first()
    if not db_config:
        raise HTTPException(status_code=404, detail="Config not found")

    # 2. 权限校验：确保只能修改自己的配置
    if db_config.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 3. 更新字段逻辑
    update_data = config_in.dict(exclude_unset=True)

    for field, value in update_data.items():
        # 特殊处理 API Key：
        # 如果前端传回的值包含 '*' (说明是掩码) 或者为空，则跳过更新，保留数据库原值
        if field == "api_key":
            if not value or "****" in value:
                continue

        # [可选] 如果你想在这里也支持更新激活状态（虽然建议用 /activate 接口）
        # 你可以添加逻辑：如果更新了 is_active_chat=True，则先把其他的置为 False
        # 这里为了安全起见，通常 Update 接口只负责修改内容，不负责切换状态

        setattr(db_config, field, value)

    db.commit()
    db.refresh(db_config)

    # Pydantic 的 response_model 会自动处理返回数据，
    # 只要 schemas.LLMConfigOut 定义了 api_key_masked 且有计算逻辑/getter
    return db_config


@router.post("/{config_id}/test")
def test_llm_config(
        config_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    config = db.query(models.LLMConfig).filter(
        models.LLMConfig.id == config_id,
        models.LLMConfig.user_id == current_user.id
    ).first()

    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    if not config.api_key:
        return {"success": False, "message": "API Key 未配置"}

    base_url = config.base_url or "https://api.openai.com/v1"
    if not config.provider or config.provider == "openai":
        base_url = config.base_url or "https://api.openai.com/v1"
    elif config.provider == "ollama":
        base_url = config.base_url or "http://localhost:11434/v1"
    elif config.provider == "deepseek":
        base_url = config.base_url or "https://api.deepseek.com/v1"
    elif config.provider == "azure_openai":
        base_url = config.base_url or ""

    success, message = test_openai_connection(
        base_url,
        config.api_key,
        config.model_name
    )

    return {"success": success, "message": message}