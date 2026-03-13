import logging
import os
import json
import base64
import uuid
import pandas as pd
from io import BytesIO
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel

# --- 导入路径修正 ---
from .. import models, schemas
from ..database import get_db
from ..rag import RagService
from ..tasks import process_knowledge_file
from .auth import get_current_user

# 引入异步 OpenAI 客户端，防止阻塞
from openai import AsyncOpenAI

router = APIRouter()
UPLOAD_DIR = "/data/uploads"


# --- [新增] 搜索请求模型 ---
class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


# --- 1. 知识库上传 ---
@router.post("/upload")
async def upload_knowledge(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # 1. 第一步：先检查是否有激活的 Embedding 模型
    llm_config = db.query(models.LLMConfig).filter(
        models.LLMConfig.user_id == current_user.id,
        models.LLMConfig.is_active_chat == True
    ).first()

    if not llm_config:
        raise HTTPException(status_code=400, detail="请先在配置页激活一个用途为'文本对话(Chat)'的模型用于向量化")

    # 2. 第二步：检查通过后，再保存文件
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    # 异步读取和写入文件
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # 3. 第三步：创建数据库记录
    new_doc = models.KnowledgeDocument(
        filename=file.filename,
        file_path=file_path,
        doc_type=file.filename.split('.')[-1],
        status="pending"
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    # 4. 第四步：触发后台任务
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
# [新增] 知识库检索测试接口
# ----------------------------------------------------------------
@router.post("/search")
def search_knowledge_base(
        req: SearchRequest,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    llm_config = db.query(models.LLMConfig).filter(
        models.LLMConfig.user_id == current_user.id,
        models.LLMConfig.is_active_chat == True
    ).first()

    if not llm_config:
        raise HTTPException(status_code=400, detail="请先激活'文本对话(Chat)'模型用于检索")

    try:
        rag = RagService(
            api_key=llm_config.api_key,
            base_url=llm_config.base_url,
            model_name=llm_config.model_name
        )

        docs = rag.search(req.query, k=req.top_k)

        results = []
        for doc in docs:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
            })

        return {"status": "success", "results": results}

    except Exception as e:
        print(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------
# 2. 用例生成 (修复：使用 AsyncOpenAI 防止阻塞)
# ----------------------------------------------------------------
@router.post("/generate")
async def generate_cases(
        requirement: str = Form(...),
        image_file: UploadFile = File(None),
        reuse_image_path: str = Form(None),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # --- A. 图片处理 ---
    final_image_path = None
    if image_file:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ext = image_file.filename.split('.')[-1]
        new_filename = f"{uuid.uuid4()}.{ext}"
        final_image_path = os.path.join(UPLOAD_DIR, new_filename)
        # 异步读取文件
        content = await image_file.read()
        with open(final_image_path, "wb") as f:
            f.write(content)
    elif reuse_image_path:
        if os.path.exists(reuse_image_path):
            final_image_path = reuse_image_path

    # --- B. 创建记录 ---
    new_record = models.TestCaseRecord(
        user_id=current_user.id,
        requirement=requirement,
        image_path=final_image_path,
        status="processing",
        result_json=[]
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    # --- C. 执行生成 ---
    try:
        # 1. 获取生成模型 (is_active_gen)
        chat_config = db.query(models.LLMConfig).filter(
            models.LLMConfig.user_id == current_user.id,
            models.LLMConfig.is_active_gen == True
        ).first()
        if not chat_config:
            raise Exception("请先激活一个用途为'用例生成(Gen)'的模型")

        # 2. 获取向量模型 (is_active_chat)
        embed_config = db.query(models.LLMConfig).filter(
            models.LLMConfig.user_id == current_user.id,
            models.LLMConfig.is_active_chat == True
        ).first()

        rag_context = ""
        if embed_config:
            try:
                # 注意：如果 RagService 初始化非常耗时，这里可能会轻微阻塞，但通常还好
                rag = RagService(
                    api_key=embed_config.api_key,
                    base_url=embed_config.base_url,
                    model_name=embed_config.model_name
                )
                docs = rag.search(requirement, k=3)
                rag_context = "\n\n".join(
                    [f"--- 参考规则/用例 {i + 1} ---\n{d.page_content}" for i, d in enumerate(docs)])
                print("rag查询")
            except Exception as e:
                print(f"RAG search failed: {e}")
                rag_context = "（暂无历史参考数据）"

        # 3. 构造 System Prompt
        system_prompt = """
你是一个资深的UI/UX测试专家。你需要根据用户的【图片】设计一条测试用例。
  !!! 核心要求 (CRITICAL INSTRUCTION) !!!
  1. **严格遵守参考风格**：输出格式必须严格模仿下方的风格（包括字段排版、分割线风格、JSON 键值结构）
      参考风格：
 ——————————————————————————————————————————
         <                      发票详情
         未申请图标                              未申请
         应收金额                                ￥210
         不可开票金额                             ￥10
         可开票金额                              ￥200
         交易类型                                 消费
         时间                     2025-01-01 10:00:00
         交易流水号
         发票状态                            未申请发票
         开具状态                              未开发票
———————————————————————————————————————————
  2. **视觉还原**：多行文本或特殊符号来模拟 UI 布局，请照做，尽量还原视觉
  3. **详细度**：不要只写“显示正确”，要写出具体的字段值。
  请输出纯 JSON 格式的列表，列表项包含：module, title, precondition, steps (数组), expected, priority (P0/P1/P2)。
  """
        messages = [{"role": "system", "content": system_prompt}]
        user_content = []

        # 4. 构造 User Prompt
        prompt_text = f"""	
        请执行：
        1. 你要先学习风格，再生成测试用例。
        2. 结合当前需求，生成覆盖 UI 交互、数据校验的测试用例。
        3. 确保输出的 JSON 格式与参考信息完全一致。
        """

        # 多模态处理
        # 兼容性处理：防止数据库没有 model_type 字段导致报错
        is_multimodal = getattr(chat_config, 'model_type', 'text') == 'multimodal'

        if is_multimodal and final_image_path:
            with open(final_image_path, "rb") as img_f:
                image_data = img_f.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')
            user_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}})
        else:
            user_content.append({"type": "text", "text": prompt_text})

        messages.append({"role": "user", "content": user_content})

        base_url = chat_config.base_url.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url += "/v1"

        client = AsyncOpenAI(
            api_key=chat_config.api_key or "ollama",  # Ollama 无需真实API Key，填任意值
            base_url=base_url,
            timeout=600.0  # 新增：全局超时
        )

        # 关键修改：使用 await 异步调用，防止阻塞
        response = await client.chat.completions.create(
            model=chat_config.model_name,
            messages=messages,
            temperature=0.2,
            max_tokens=2500,
            timeout=600,
            extra_body={"enable_thinking": False, "verbose": False},
        )
        res_content = response.choices[0].message.content

        # 使用qwen3.5-27b的处理 lmstudio部署
        content = res_content.strip().split("```json")[1]

        if content.startswith("```json"): content = content[7:]
        if content.startswith("```"): content = content[3:]

        if content.endswith("```"): content = content[:-3]
        result_json = json.loads(content.strip())

        new_record.result_json = result_json
        new_record.status = "success"

    except Exception as e:
        logging.error(f"Generation failed: {e}")
        new_record.status = "failed"
        new_record.error_msg = str(e)
    finally:
        db.commit()

    return {"status": "success", "record_id": new_record.id}


# --- 3. 生成记录管理接口 (保持不变) ---
@router.get("/records")
def get_records(
        skip: int = 0,
        limit: int = 20,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    records = db.query(models.TestCaseRecord) \
        .filter(models.TestCaseRecord.user_id == current_user.id) \
        .order_by(desc(models.TestCaseRecord.id)) \
        .offset(skip).limit(limit).all()
    return records


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


# --- 4. 导出 Excel (保持不变) ---
@router.post("/export")
def export_excel(cases: list[dict]):
    df = pd.DataFrame(cases)
    rename_map = {
        "module": "模块", "title": "用例标题", "precondition": "前置条件",
        "steps": "测试步骤", "expected": "预期结果", "priority": "优先级"
    }
    df = df.rename(columns=rename_map)
    output = BytesIO()

    # 使用 xlsxwriter 引擎
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='GeneratedCases')

        # 1. 获取 workbook 和 worksheet 对象
        workbook = writer.book
        worksheet = writer.sheets['GeneratedCases']

        # 2. 定义格式：自动换行 + 垂直居中(或顶部对齐) + 边框
        wrap_format = workbook.add_format({
            'text_wrap': True,  # 核心：开启自动换行
            'valign': 'top',  # 建议：内容顶部对齐，这就不会因为行高太高而看着难受
            'align': 'left',  # 建议：左对齐
            'border': 1  # 可选：加个边框更好看
        })

        # 3. 设置列宽的同时，应用这个格式
        # set_column(start_col, end_col, width, cell_format)
        worksheet.set_column('A:B', 20, wrap_format)  # 模块、标题
        worksheet.set_column('C:C', 30, wrap_format)  # 前置条件
        worksheet.set_column('D:E', 50, wrap_format)  # 步骤、预期结果 (这两列内容最长，必须换行)
        worksheet.set_column('F:F', 10, wrap_format)  # 优先级

    output.seek(0)
    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={"Content-Disposition": "attachment; filename=test_cases.xlsx"}
    )


# --- 5. RAG 工具接口 (修正模型引用) ---

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
        models.LLMConfig.is_active_chat == True
    ).first()

    if not llm_config:
        raise HTTPException(status_code=400, detail="请先激活'文本(Chat)'模型用于向量化")

    llm_config_dict = {
        "api_key": llm_config.api_key,
        "base_url": llm_config.base_url,
        "model_name": llm_config.model_name or "nomic-embed-text",
        "model_family": getattr(llm_config, 'model_family', '')
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
    # 1. 查找文件记录
    doc = db.query(models.KnowledgeDocument).filter(models.KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")

    print(f"------------ [DEBUG START] 删除流程 ID={doc_id} ------------")
    print(f"1. 准备删除文件: {doc.filename}")

    # 2. 查找是否配置了 Embedding 模型
    llm_config = db.query(models.LLMConfig).filter(
        models.LLMConfig.user_id == current_user.id,
        models.LLMConfig.is_active_chat == True
    ).first()

    if llm_config:
        print(f"2. ✅ 发现已激活的 Embedding 模型: {llm_config.model_name}")
        try:
            print("3. 正在初始化 RagService...")
            rag = RagService(
                api_key=llm_config.api_key,
                base_url=llm_config.base_url,
                model_name=llm_config.model_name
            )

            path_str = str(doc.file_path)
            print(f"4. 🚀 调用 rag.delete_doc_by_source, 路径: {path_str}")

            rag.delete_doc_by_source(path_str)
            print("5. RagService 调用结束")

        except Exception as e:
            print(f"❌ [API Error] 向量删除步骤抛出异常: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("⚠️ [跳过] 未找到激活的 'is_active_chat' 模型，跳过向量删除步骤！")

    # 3. 物理文件删除
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
            print(f"6. ✅ 物理文件已删除: {doc.file_path}")
        except Exception as e:
            print(f"❌ 物理文件删除失败: {e}")
    else:
        print(f"6. ⚠️ 物理文件不存在，无需删除: {doc.file_path}")

    # 4. 数据库记录删除
    db.delete(doc)
    db.commit()
    print(f"7. 数据库记录已清除")
    print(f"------------ [DEBUG END] ------------")

    return {"status": "success", "msg": "删除成功"}