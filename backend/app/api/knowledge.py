import logging
import os
import json
import base64
import uuid  # [新增] 用于生成文件名
import pandas as pd
from io import BytesIO
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc  # [新增] 用于排序

# --- 导入路径修正 ---
from .. import models, schemas
from ..database import get_db
from ..rag import RagService
from ..tasks import process_knowledge_file
from .auth import get_current_user

router = APIRouter()
UPLOAD_DIR = "/app/uploads"


# --- 1. 知识库上传 (保持不变) ---
@router.post("/upload")
async def upload_knowledge(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    new_doc = models.KnowledgeDocument(
        filename=file.filename,
        file_path=file_path,
        doc_type=file.filename.split('.')[-1],
        status="pending"
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    llm_config = db.query(models.LLMConfig).filter(
        models.LLMConfig.user_id == current_user.id,
        models.LLMConfig.is_active == True,
        models.LLMConfig.use_for == "embedding"
    ).first()

    if not llm_config:
        raise HTTPException(status_code=400, detail="请先在配置页激活一个用途为'向量化(Embedding)'的模型")

    llm_config_dict = {
        "api_key": llm_config.api_key,
        "base_url": llm_config.base_url,
        "model_name": llm_config.model_name,
    }

    process_knowledge_file.delay(new_doc.id, llm_config_dict)

    return {"status": "success", "id": new_doc.id}


@router.get("/list")
def get_knowledge_list(db: Session = Depends(get_db)):
    return db.query(models.KnowledgeDocument).order_by(models.KnowledgeDocument.id.desc()).all()


# ----------------------------------------------------------------
# 2. 用例生成 (核心修改：存库模式)
# ----------------------------------------------------------------
@router.post("/generate")
async def generate_cases(
        requirement: str = Form(...),
        image_file: UploadFile = File(None),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # --- A. 保存图片到本地 (如果存在) ---
    image_path = None
    if image_file:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        # 获取后缀
        ext = image_file.filename.split('.')[-1]
        # 使用 UUID 生成唯一文件名，防止覆盖
        new_filename = f"{uuid.uuid4()}.{ext}"
        image_path = os.path.join(UPLOAD_DIR, new_filename)

        # 保存文件
        content = await image_file.read()
        with open(image_path, "wb") as f:
            f.write(content)

    # --- B. 创建数据库记录 (状态: processing) ---
    # 注意：models.TestCaseRecord 需要你已经在 models.py 中定义好
    new_record = models.TestCaseRecord(
        user_id=current_user.id,  # 这里直接存 int ID，因为取消了外键
        requirement=requirement,
        image_path=image_path,
        status="processing",
        result_json=[]
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    # --- C. 执行生成逻辑 (同步执行，完成后更新库) ---
    try:
        # 1. 获取生成/对话模型
        chat_config = db.query(models.LLMConfig).filter(
            models.LLMConfig.user_id == current_user.id,
            models.LLMConfig.is_active == True,
            models.LLMConfig.use_for == "generation"
        ).first()

        if not chat_config:
            raise Exception("请先激活一个用途为'生成/测试(Generation)'的大模型")

        # 2. 获取向量模型 & RAG 检索
        embed_config = db.query(models.LLMConfig).filter(
            models.LLMConfig.user_id == current_user.id,
            models.LLMConfig.is_active == True,
            models.LLMConfig.use_for == "embedding"
        ).first()

        rag_context = ""
        if embed_config:
            try:
                rag = RagService(
                    api_key=embed_config.api_key,
                    base_url=embed_config.base_url,
                    model_name=embed_config.model_name
                )
                docs = rag.search(requirement, k=3)  # 减少数量加快速度
                rag_context = "\n---\n".join([d.page_content for d in docs])
            except Exception as e:
                print(f"RAG search failed: {e}")
                rag_context = "（暂无历史参考数据）"

        # 3. 构造 System Prompt (保持严格模仿指令)
        system_prompt = """
        你是一个资深的QA测试专家。你需要根据用户的【需求描述】和可选的【产品截图】设计测试用例。

        !!! 核心要求 (CRITICAL INSTRUCTION) !!!
        你的输出风格必须 **严格模仿** 下文提供的【历史参考用例】。

        1. 【格式模仿】：如果历史用例的“预期结果”使用了“视觉化布局”（例如包含 '——————' 分割线、换行展示所有字段、KV结构），你必须完全照做！严禁将它们合并为一句话。
        2. 【排版】：在 JSON 字符串中，使用 '\\n' 来表示换行，确保前端展示时能还原 UI 布局感。
        3. 【详细度】：不要只写“显示正确”，要像历史用例那样，写出具体的字段值（参考截图中的真实数值）。

        请输出纯 JSON 格式的列表，列表项包含：module, title, precondition, steps (数组), expected, priority (P0/P1/P2)。
        """

        messages = [{"role": "system", "content": system_prompt}]
        user_content = []

        # 4. 构造 User Prompt
        prompt_text = f"""
        【当前需求描述】：
        {requirement}

        【历史参考用例 (这是你的风格模板，请严格模仿其写法)】：
        {rag_context}

        请注意：
        1. 内容上：结合【图片】（如果有）中的实际文案和数值。
        2. 格式上：完全照搬【历史参考用例】的排版方式（包括换行、分割线、语气）。
        """

        # --- 处理图片逻辑 (从本地路径读取) ---
        if chat_config.model_type == 'multimodal' and image_path:
            # 读取刚才保存的文件
            with open(image_path, "rb") as img_f:
                image_data = img_f.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')

            user_content.append({
                "type": "text",
                "text": prompt_text + "\n请结合上传的产品截图进行设计。"
            })
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"  # 假设是jpeg/png
                }
            })
        else:
            user_content.append({"type": "text", "text": prompt_text})

        messages.append({"role": "user", "content": user_content})

        # 5. 调用 LLM
        from openai import OpenAI
        client = OpenAI(
            api_key=chat_config.api_key,
            base_url=chat_config.base_url
        )

        response = client.chat.completions.create(
            model=chat_config.model_name,
            messages=messages,
            temperature=0.2,
            max_tokens=2500
        )

        res_content = response.choices[0].message.content

        # 6. 解析结果
        content = res_content.strip()
        if content.startswith("```json"): content = content[7:]
        if content.startswith("```"): content = content[3:]
        if content.endswith("```"): content = content[:-3]

        result_json = json.loads(content.strip())

        # --- D. 更新数据库成功状态 ---
        new_record.result_json = result_json
        new_record.status = "success"

    except Exception as e:
        logging.error(f"Generation failed: {e}")
        new_record.status = "failed"
        new_record.error_msg = str(e)
    finally:
        db.commit()

    # 返回记录ID，前端拿到ID后可以跳转详情或刷新列表
    return {"status": "success", "record_id": new_record.id}


# ----------------------------------------------------------------
# 3. 生成记录管理接口 (新增)
# ----------------------------------------------------------------

# 获取历史列表
@router.get("/records")
def get_records(
        skip: int = 0,
        limit: int = 20,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # 因为 models.py 取消了外键，这里直接对比 integer 类型的 user_id
    records = db.query(models.TestCaseRecord) \
        .filter(models.TestCaseRecord.user_id == current_user.id) \
        .order_by(desc(models.TestCaseRecord.id)) \
        .offset(skip).limit(limit).all()
    return records


# 获取单条详情
@router.get("/records/{record_id}")
def get_record_detail(
        record_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    record = db.query(models.TestCaseRecord).filter(
        models.TestCaseRecord.id == record_id,
        models.TestCaseRecord.user_id == current_user.id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    return record


# ----------------------------------------------------------------
# 4. 导出 Excel (支持批量)
# ----------------------------------------------------------------
@router.post("/export")
def export_excel(cases: list[dict]):
    # 这个接口本身就支持接收 list，所以支持批量导出
    # 前端只要把选中的行组成的数组传过来即可
    df = pd.DataFrame(cases)

    # 兼容中英文键名
    rename_map = {
        "module": "模块", "title": "用例标题", "precondition": "前置条件",
        "steps": "测试步骤", "expected": "预期结果", "priority": "优先级"
    }
    df = df.rename(columns=rename_map)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='GeneratedCases')

        # 简单美化列宽
        worksheet = writer.sheets['GeneratedCases']
        worksheet.set_column('A:B', 20)
        worksheet.set_column('C:C', 30)
        worksheet.set_column('D:E', 50)

    output.seek(0)

    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={"Content-Disposition": "attachment; filename=test_cases.xlsx"}
    )


# --- 5. RAG 工具接口 (保持不变) ---

@router.post("/{doc_id}/reprocess")
async def reprocess_knowledge(
        doc_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    doc = db.query(models.KnowledgeDocument).filter(models.KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")

    llm_config = db.query(models.LLMConfig).filter(
        models.LLMConfig.user_id == current_user.id,
        models.LLMConfig.is_active == True,
        models.LLMConfig.use_for == "embedding"
    ).first()

    if not llm_config:
        raise HTTPException(status_code=400, detail="请先在配置页激活一个用途为'向量化(Embedding)'的模型")

    llm_config_dict = {
        "api_key": llm_config.api_key,
        "base_url": llm_config.base_url,
        "model_name": llm_config.model_name or "nomic-embed-text",
        "model_family": llm_config.model_family
    }

    doc.status = "pending"
    doc.error_msg = None
    db.commit()

    process_knowledge_file.delay(doc.id, llm_config_dict)

    return {"status": "success", "msg": "已提交重新解析任务"}


@router.delete("/{doc_id}")
def delete_knowledge(
        doc_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    doc = db.query(models.KnowledgeDocument).filter(models.KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")

    llm_config = db.query(models.LLMConfig).filter(
        models.LLMConfig.user_id == current_user.id,
        models.LLMConfig.is_active == True,
        models.LLMConfig.use_for == "embedding"
    ).first()

    if llm_config:
        try:
            rag = RagService(
                api_key=llm_config.api_key,
                base_url=llm_config.base_url,
                model_name=llm_config.model_name
            )
            rag.delete_doc_by_source(doc.file_path)
        except Exception as e:
            print(f"Warning: Failed to cleanup vectors for {doc.filename}: {e}")

    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception as e:
            print(f"Error deleting file {doc.file_path}: {e}")

    db.delete(doc)
    db.commit()

    return {"status": "success", "msg": "删除成功"}