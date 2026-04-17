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
import re


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
    logging.info(f"[知识库上传] 用户 {current_user.username} 开始上传文件: {file.filename}")
    
    # 1. 第一步：先检查是否有激活的 Embedding 模型
    llm_config = db.query(models.LLMConfig).filter(
        models.LLMConfig.user_id == current_user.id,
        models.LLMConfig.is_active_chat == True
    ).first()

    if not llm_config:
        logging.warning(f"[知识库上传] 用户 {current_user.username} 未配置激活的 Embedding 模型")
        raise HTTPException(status_code=400, detail="请先在配置页激活一个用途为'文本对话(Chat)'的模型用于向量化")
    
    logging.info(f"[知识库上传] 找到激活的 Embedding 模型: {llm_config.model_name}")

    # 2. 第二步：检查通过后，再保存文件
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    logging.info(f"[知识库上传] 文件保存路径: {file_path}")

    # 异步读取和写入文件
    content = await file.read()
    file_size = len(content)
    logging.info(f"[知识库上传] 文件大小: {file_size} bytes")

    with open(file_path, "wb") as f:
        f.write(content)
    logging.info(f"[知识库上传] 文件写入成功")

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
    logging.info(f"[知识库上传] 数据库记录创建成功，文档ID: {new_doc.id}")

    # 4. 第四步：触发后台任务
    llm_config_dict = {
        "api_key": llm_config.api_key,
        "base_url": llm_config.base_url,
        "model_name": llm_config.model_name,
    }
    logging.info(f"[知识库上传] 触发后台处理任务，任务ID: {new_doc.id}")

    process_knowledge_file.delay(new_doc.id, llm_config_dict)
    logging.info(f"[知识库上传] 后台任务已提交")

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
        logging.error(f"[知识库检索] 搜索失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------
# 2. 用例生成 (修复：使用 AsyncOpenAI 防止阻塞)
# ----------------------------------------------------------------
@router.post("/generate")
async def generate_cases(
        requirement: str = Form(...),
        image_file: UploadFile = File(None),
        reuse_image_path: str = Form(None),
        skill_id: int = Form(None),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    logging.info(f"[用例生成] ========== 开始用例生成任务 ==========")
    logging.info(f"[用例生成] 用户: {current_user.username}, 需求长度: {len(requirement)}")
    logging.info(f"[用例生成] 图片上传: {'是' if image_file else '否'}, 复用路径: {reuse_image_path}, 技能ID: {skill_id}")
    
    # --- A. 图片处理 ---
    final_image_path = None
    if image_file:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ext = image_file.filename.split('.')[-1]
        new_filename = f"{uuid.uuid4()}.{ext}"
        final_image_path = os.path.join(UPLOAD_DIR, new_filename)
        logging.info(f"[用例生成] 处理上传图片: {image_file.filename} -> {final_image_path}")
        # 异步读取文件
        content = await image_file.read()
        logging.info(f"[用例生成] 图片大小: {len(content)} bytes")
        with open(final_image_path, "wb") as f:
            f.write(content)
        logging.info(f"[用例生成] 图片保存成功")
    elif reuse_image_path:
        if os.path.exists(reuse_image_path):
            final_image_path = reuse_image_path
            logging.info(f"[用例生成] 复用已有图片: {reuse_image_path}")
        else:
            logging.warning(f"[用例生成] 指定的图片路径不存在: {reuse_image_path}")

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
    logging.info(f"[用例生成] 创建处理记录，ID: {new_record.id}")

    # --- C. 执行生成 ---
    try:
        logging.info(f"[用例生成] 开始获取模型配置...")
        # 1. 获取生成模型 (is_active_gen)
        chat_config = db.query(models.LLMConfig).filter(
            models.LLMConfig.user_id == current_user.id,
            models.LLMConfig.is_active_gen == True
        ).first()
        if not chat_config:
            logging.error(f"[用例生成] 未找到激活的生成模型 (is_active_gen)")
            raise Exception("请先激活一个用途为'用例生成(Gen)'的模型")
        logging.info(f"[用例生成] 使用生成模型: {chat_config.model_name} @ {chat_config.base_url}")

        # 2. 获取向量模型 (is_active_chat)
        embed_config = db.query(models.LLMConfig).filter(
            models.LLMConfig.user_id == current_user.id,
            models.LLMConfig.is_active_chat == True
        ).first()
        if embed_config:
            logging.info(f"[用例生成] 使用向量模型: {embed_config.model_name}")
        else:
            logging.warning(f"[用例生成] 未找到向量模型，跳过 RAG 上下文")

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
                logging.info(f"[用例生成] RAG查询成功，获取到 {len(docs)} 条参考文档")
            except Exception as e:
                logging.warning(f"[用例生成] RAG搜索失败: {e}，使用默认上下文")
                rag_context = "（暂无历史参考数据）"
        
        # 3. 获取技能提示词（新增）
        system_prompt = None
        skill_name = None
        logging.info(f"[用例生成] 技能处理开始 - skill_id: {skill_id}, 类型: {type(skill_id)}")
        
        if skill_id:
            skill = db.query(models.Skill).filter(
                models.Skill.id == skill_id,
                models.Skill.is_active == True
            ).first()
            logging.info(f"[用例生成] 技能查询结果: {'找到' if skill else '未找到'}")
            
            if skill:
                logging.info(f"[用例生成] 技能详情 - 名称: {skill.name}, 类型: {skill.skill_type}")
                # 校验技能类型：如果上传了图片，文本类型的技能无效
                if final_image_path and skill.skill_type == "text":
                    logging.warning(f"[用例生成] 技能 '{skill.name}' 是文本类型，但用户上传了图片，使用默认提示词")
                    system_prompt = None
                    skill_name = None
                else:
                    system_prompt = skill.prompt_content
                    skill_name = skill.name
                    logging.info(f"[用例生成] 成功应用技能提示词，长度: {len(system_prompt)} 字符")
            else:
                logging.warning(f"[用例生成] 技能ID {skill_id} 不存在或未启用，使用默认提示词")
        
        logging.info(f"[用例生成] 最终 system_prompt 状态: {'已设置' if system_prompt else 'None (使用默认)'}")
        logging.info(f"[用例生成] 技能处理结束")
        
        user_content = []
        messages = None
        if final_image_path:
            # 如果没有使用技能，使用默认图片提示词
            if system_prompt is None:
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
                                  3. **详细度**：不要只写"显示正确"，要写出具体的字段值。
                                  请输出纯 JSON 格式的列表，列表项包含：module, title, precondition, steps (数组), expected, priority (P0/P1/P2)。
                                  """
            messages = [{"role": "system", "content": system_prompt}]

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
                user_content.append({"type": "text", "text": prompt_text + "\n请结合上传的产品截图进行设计。"})
                user_content.append(
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}})
            else:
                user_content.append({"type": "text", "text": prompt_text})

            messages.append({"role": "user", "content": user_content})
        else:
            # 如果没有使用技能，使用默认文本提示词
            if system_prompt is None:
                system_prompt = """
                                
## Role: 高级测试工程师
### Profile
- language: 中文
- description: 专业从事复杂系统测试设计的质量保障专家
- background: 10年PaaS/云平台/金融/电商领域测试经验，ISTQB认证专家
- personality: 严谨细致，逻辑性强，风险敏感
- expertise: 测试策略制定、场景建模、异常流覆盖
- target_audience: 测试团队/开发团队/质量保障部门

## Rules
### 1. 测试设计能力
- 等价类划分: 精准识别有效/无效等价类边界
- 场景分析法: 构建用户旅程地图识别关键路径
- 正交分解: 处理多参数组合场景
- 状态迁移: 验证复杂状态转换逻辑

### 2. 设计原则
- MECE原则: 用例集合相互独立且完全穷尽
- 风险优先: 按失效影响度分配测试强度

### 3. 执行准则
- 原子操作: 单用例验证单一功能点
- 正向优先: 70%用例覆盖正常业务流程
- 逆向覆盖: 30%用例验证异常处理机制
- 生成零遗漏的测试用例集
- 补充边界值/异常流用例
- 用例数量要求: 达到路径覆盖率100%，覆盖所有需求内容

### 4. 格式约束
- 用例步骤: 每个用例需2个以上步骤，建议2~5步
- 结果明确: 每个预期结果包含可验证断言
- 优先级定义: P0(最高)/P1(高)/P2(中)/P3(低)
- 特性标注: 功能/性能/安全/兼容性
- 【强制】全文禁止使用中文括号()，仅允许使用英文括号()或不使用括号

### 5. 用例标题命名规范
格式: 模块功能-操作-条件-预期结果
- 功能: 明确测试所属模块或核心功能
- 操作/场景: 用户执行的具体操作
- 条件: 前置条件、输入参数、边界条件
- 预期结果: 简述用例预期输出

## 输出格式要求【强制】
1. 仅输出标准JSON数组，无多余文字、无注释、无代码块
2. 字段固定，不可增减、不可改名： module, title, precondition, steps (数组，需要编号), expected(需要编号), priority (P0/P1/P2)。
3. 测试步骤与预期结果必须一一对应，数量一致
4. 正向用例占比70%，逆向用例占比30%
5. 字段内容禁止出现中文括号，避免接口解析失败

## 工作流程
### 步骤1: 分析需求
- 理解业务需求和功能点
- 识别关键路径和边界条件
- 确定测试策略

### 步骤2: 生成测试用例
- 严格按照规则生成标准JSON格式用例
- 覆盖所有需求，路径覆盖率100%

### 步骤3: 格式校验
- 校验JSON格式合法性
- 校验字段完整性
- 校验无中文括号
- 校验步骤与结果一一对应
"""
            messages = [{"role": "system", "content": system_prompt}]

            prompt_text = f"""
                    【当前需求描述】：
                    {requirement}
                    【知识库参考信息 (这是必须遵守的业务规则和风格)】：
                    {rag_context}
                    """
            user_content.append({"type": "text", "text": prompt_text})

            messages.append({"role": "user", "content": user_content})

        base_url = chat_config.base_url.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url += "/v1"
        logging.info(f"[用例生成] LLM API 地址: {base_url}")

        client = AsyncOpenAI(
            api_key=chat_config.api_key or "ollama",  # Ollama 无需真实API Key，填任意值
            base_url=base_url,
            timeout=600.0  # 新增：全局超时
        )
        logging.info(f"[用例生成] 准备调用 LLM，模型: {chat_config.model_name}")

        # 关键修改：使用 await 异步调用，防止阻塞
        try:
            response = await client.chat.completions.create(
                model=chat_config.model_name,
                messages=messages,
                temperature=0.2,
                max_tokens=8192,
                timeout=600,
                extra_body={"enable_thinking": False, "verbose": False},
            )
            logging.info(f"[用例生成] LLM 调用成功，响应长度: {len(response.choices[0].message.content)}")
        except Exception as e:
            logging.error(f"[用例生成] LLM 调用失败: {e}", exc_info=True)
            raise
        
        res_content = response.choices[0].message.content

        # 使用qwen3.5-27b的处理 lmstudio部署
        # 步骤1：清理首尾空白
        clean_content = res_content.strip()

        # 步骤2：如果开头是 <think>，截掉 <think></think> 标签
        if clean_content.startswith("<think>"):
            # 找到 </think> 标签的位置
            end_think_pos = clean_content.find("</think>")
            if end_think_pos != -1:
                # 截取 </think> 之后的内容
                clean_content = clean_content[end_think_pos + len("</think>"):].strip()

        # 步骤3：尝试提取 JSON 代码块
        json_match = re.search(r'```json\s*(.*?)\s*```', clean_content, re.DOTALL)

        if json_match:
            json_str = json_match.group(1).strip()
        else:
            # 如果没有代码块标记，尝试直接解析整个内容
            json_str = clean_content
        
        logging.info(f"[用例生成] LLM 返回结果长度: {len(json_str)} 字符")
        logging.debug(f"[用例生成] LLM 返回结果预览: {json_str}")
        
        new_record.result_json = json.loads(json_str)
        new_record.status = "success"
        logging.info(f"[用例生成] 用例生成成功，记录ID: {new_record.id}, 用例数量: {len(new_record.result_json)}")

    except Exception as e:
        logging.error(f"[用例生成] 用例生成失败: {e}", exc_info=True)
        new_record.status = "failed"
        new_record.error_msg = str(e)
        logging.error(f"[用例生成] 更新记录状态为 failed，错误信息: {str(e)}")
    finally:
        db.commit()
        logging.info(f"[用例生成] ========== 用例生成任务结束 ==========")

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
    # 处理测试步骤和预期结果，将数组转换为带换行符的字符串
    processed_cases = []
    for case in cases:
        processed_case = case.copy()
        # 处理测试步骤
        if isinstance(processed_case.get('steps'), list):
            processed_case['steps'] = '\n'.join(processed_case['steps'])
        # 处理预期结果
        if isinstance(processed_case.get('expected'), list):
            processed_case['expected'] = '\n'.join(processed_case['expected'])
        processed_cases.append(processed_case)
    
    df = pd.DataFrame(processed_cases)
    rename_map = {
        "module": "模块", "title": "用例标题", "priority": "优先级",
        "precondition": "前置条件", "steps": "测试步骤", "expected": "预期结果"
    }
    # 调整列顺序
    df = df[["module", "title", "priority", "precondition", "steps", "expected"]]
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
        worksheet.set_column('C:C', 10, wrap_format)  # 优先级
        worksheet.set_column('D:D', 30, wrap_format)  # 前置条件
        worksheet.set_column('E:F', 50, wrap_format)  # 步骤、预期结果 (这两列内容最长，必须换行)

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
    logging.info(f"[知识库重新处理] 用户 {current_user.username} 请求重新处理文档 ID: {doc_id}")
    
    doc = db.query(models.KnowledgeDocument).filter(models.KnowledgeDocument.id == doc_id).first()
    if not doc:
        logging.error(f"[知识库重新处理] 文档 ID {doc_id} 不存在")
        raise HTTPException(status_code=404, detail="文件不存在")
    logging.info(f"[知识库重新处理] 找到文档: {doc.filename}, 当前状态: {doc.status}")

    llm_config = db.query(models.LLMConfig).filter(
        models.LLMConfig.user_id == current_user.id,
        models.LLMConfig.is_active_chat == True
    ).first()

    if not llm_config:
        logging.error(f"[知识库重新处理] 用户 {current_user.username} 未配置激活的 Embedding 模型")
        raise HTTPException(status_code=400, detail="请先激活'文本(Chat)'模型用于向量化")
    logging.info(f"[知识库重新处理] 使用模型: {llm_config.model_name}")

    llm_config_dict = {
        "api_key": llm_config.api_key,
        "base_url": llm_config.base_url,
        "model_name": llm_config.model_name or "nomic-embed-text",
        "model_family": getattr(llm_config, 'model_family', '')
    }
    logging.info(f"[知识库重新处理] 配置 LLM 参数完成")

    doc.status = "pending"
    doc.error_msg = None
    db.commit()
    logging.info(f"[知识库重新处理] 文档状态已更新为 pending")

    process_knowledge_file.delay(doc.id, llm_config_dict)
    logging.info(f"[知识库重新处理] 后台任务已提交，文档ID: {doc.id}")

    return {"status": "success", "msg": "已提交重新解析任务"}


@router.delete("/{doc_id}")
def delete_knowledge(
        doc_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    logging.info(f"[知识库删除] ========== 开始删除文档 ID: {doc_id} ==========")
    logging.info(f"[知识库删除] 用户: {current_user.username}")
    
    # 1. 查找文件记录
    doc = db.query(models.KnowledgeDocument).filter(models.KnowledgeDocument.id == doc_id).first()
    if not doc:
        logging.error(f"[知识库删除] 文档 ID {doc_id} 不存在")
        raise HTTPException(status_code=404, detail="文件不存在")

    logging.info(f"[知识库删除] 找到文档: {doc.filename}, 文件路径: {doc.file_path}")

    # 2. 查找是否配置了 Embedding 模型
    llm_config = db.query(models.LLMConfig).filter(
        models.LLMConfig.user_id == current_user.id,
        models.LLMConfig.is_active_chat == True
    ).first()

    if llm_config:
        logging.info(f"[知识库删除] 发现已激活的 Embedding 模型: {llm_config.model_name}")
        try:
            logging.info(f"[知识库删除] 正在初始化 RagService...")
            rag = RagService(
                api_key=llm_config.api_key,
                base_url=llm_config.base_url,
                model_name=llm_config.model_name
            )

            path_str = str(doc.file_path)
            logging.info(f"[知识库删除] 调用 rag.delete_doc_by_source, 路径: {path_str}")

            rag.delete_doc_by_source(path_str)
            logging.info(f"[知识库删除] 向量数据库删除成功")

        except Exception as e:
            logging.error(f"[知识库删除] 向量删除步骤失败: {e}", exc_info=True)
    else:
        logging.warning(f"[知识库删除] 未找到激活的 Embedding 模型，跳过向量删除步骤")

    # 3. 物理文件删除
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
            logging.info(f"[知识库删除] 物理文件已删除: {doc.file_path}")
        except Exception as e:
            logging.error(f"[知识库删除] 物理文件删除失败: {e}", exc_info=True)
    else:
        logging.warning(f"[知识库删除] 物理文件不存在，无需删除: {doc.file_path}")

    # 4. 数据库记录删除
    db.delete(doc)
    db.commit()
    logging.info(f"[知识库删除] 数据库记录已清除")
    logging.info(f"[知识库删除] ========== 删除流程结束 ==========")

    return {"status": "success", "msg": "删除成功"}