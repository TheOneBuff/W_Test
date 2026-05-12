from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
import base64
import json
import re
from openai import AsyncOpenAI

router = APIRouter()


# --- 纯逻辑辅助函数 (仅用于处理 LLM 返回的文本) ---

def clean_diffs_logic(diffs):
    """
    深度清洗 LLM 返回的差异数据，专门解决 'A 变更为 A' 的幻觉问题
    """
    valid_diffs = []
    seen_reasons = set()

    for item in diffs:
        reason = item.get("reason", "").strip()
        diff_type = item.get("type", "")

        # 1. 基础空值检查
        if not reason:
            continue

        # 2. 去重（完全相同的描述）
        if reason in seen_reasons:
            continue
        seen_reasons.add(reason)

        # 3. 核心：智能正则提取并比对
        # 能够匹配：
        # - "字段 'A' 在图1中为 'B'，在图2中为 'C'"
        # - "标题 Key 由 'B' 变更为 'C'"
        # - "预期为 'B'，实际为 'C'"

        # 移除标点以减少干扰
        clean_reason = re.sub(r"[，。;]", " ", reason)

        # 提取引号内的内容 (支持单引号和双引号)
        # 逻辑：找出句子中出现的两个关键文本块进行比对
        quoted_values = re.findall(r"['\"](.*?)['\"]", clean_reason)

        is_hallucination = False

        # 如果句子中提取到了两个及以上的引用值（通常前两个就是对比值）
        if len(quoted_values) >= 2:
            val1 = quoted_values[0].strip()
            val2 = quoted_values[1].strip()

            # 如果两个提取出的值完全相等，这就是幻觉
            if val1 == val2:
                is_hallucination = True
                print(f"检测到幻觉并过滤: {reason}")  # 调试日志

        # 4. 关键词兜底 (如果正则没提取到，但句子包含自相矛盾的描述)
        # 有些模型会说 "图1是X，图2也是X，不一致"
        if not is_hallucination:
            # 简单的分割判断，防止复杂句式漏网
            # 这是一个启发式规则，假设句子是对称结构的
            parts = re.split(r"变更为|变为|实际为|在图2中为", clean_reason)
            if len(parts) == 2:
                # 极简模糊比对：如果前后两部分包含相同的长关键词，可能也是幻觉
                pass

        if not is_hallucination:
            valid_diffs.append(item)

    return valid_diffs


def try_repair_json(json_str):
    """尝试修复不完整的 JSON 字符串"""
    json_str = json_str.strip()

    # 简单的括号补全
    if not json_str.endswith("}"):
        if json_str.endswith("]"):
            json_str += "}"
        else:
            json_str += "]}"

    try:
        return json.loads(json_str)
    except:
        try:
            # 正则提取兜底
            pattern = r'\{\s*"type":\s*".*?",\s*"reason":\s*".*?"\s*\}'
            matches = re.findall(pattern, json_str)
            if matches:
                # 限制数量防止过长
                valid_items = ",".join(matches[:20])
                return json.loads(f'{{"diffs": [{valid_items}]}}')
        except:
            return {"diffs": []}
    return {"diffs": []}


# --- 核心接口 ---

@router.post("/ai-diff")
async def check_visual_diff(
        file1: UploadFile = File(...),
        file2: UploadFile = File(...),
        prompt_hint: str = Form(default="找出所有key不一致的地方"),
        db: Session = Depends(get_db)
):
    # 1. 直接读取文件二进制数据
    f1_bytes = await file1.read()
    f2_bytes = await file2.read()

    # 2. 直接转 Base64 (无任何压缩/处理)
    b64_1 = base64.b64encode(f1_bytes).decode('utf-8')
    b64_2 = base64.b64encode(f2_bytes).decode('utf-8')

    # 3. 获取 LLM 配置
    llm_config = db.query(models.LLMConfig).filter(models.LLMConfig.is_active_gen == True).first()
    if not llm_config:
        raise HTTPException(status_code=400, detail="未配置或激活生成模型 (is_active_gen)")

    # 4. 构造 Prompt
    # [修改说明] 融合了您的"核心要求"，并强制要求返回 JSON 格式，否则代码无法解析
    system_prompt = """
    你是一个拥有像素级观察力的UI自动化测试专家。你的任务是对比两张图片（图1:基准 vs 图2:实际），并**仅**输出确凿的差异。

【核心检测标准】
1. ✅ 文字视觉层一致性（Key文字）：
   - 必须逐字核对字段名称、标签、标题。
   - ⚠️ 严禁幻觉：如果图1文字为 "A"，图2文字也为 "A"，绝对不能报告差异！
   - 忽略项：具体数值（如金额、日期）、用户填写的动态内容。

2. ✅ 布局结构一致性：
   - 检查模块顺序、对齐方式、元素是否存在。
   - 忽略项：轻微的像素级间距差异、颜色色值差异（除非导致文字不可见）。

【思维链与自检机制】
在输出结果前，请必须执行以下逻辑判断：
1. 提取图1的文本 -> T1。
2. 提取图2对应位置的文本 -> T2。
3. 判断：IF (T1 == T2) THEN { 丢弃该条目，不要写入JSON }。
4. 只有当 T1 与 T2 确实不同时，才记录。

【输出格式要求】
- 仅返回纯 JSON 格式。
- 如果未发现有效差异，"diffs" 数组必须为空。

JSON 结构示例：
{
  "diffs": [
    {
      "type": "Key文字", 
      "reason": "字段 '发票详情' 在图1中为 '发票详情'，在图2中为 '发票清单'，发生变更。"
    }
  ]
}

【禁止事项】
❌ 禁止报告内容相同的“差异”，例如：“字段X在图1为A，在图2为A，存在不一致”。
❌ 禁止包含 Markdown 标记（如 ```json）。
    """

    user_msg = f"指令: {system_prompt}。额外关注点: {prompt_hint}。请返回JSON。"

    # 5. 调用大模型
    client = AsyncOpenAI(api_key=llm_config.api_key, base_url=llm_config.base_url)
    try:
        resp = await client.chat.completions.create(
            model=llm_config.model_name or "gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": user_msg},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_1}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_2}"}}
                ]}
            ],
            max_tokens=2000,
            temperature=0.1
        )

        content = resp.choices[0].message.content

        # 6. 解析结果
        cleaned = re.sub(r"```json|```", "", content).strip()
        data = try_repair_json(cleaned)
        raw_diffs = data.get("diffs", [])

        # 简单清洗
        final_diffs = clean_diffs_logic(raw_diffs)

        return {
            "diff_count": len(final_diffs),
            "details": final_diffs,
            "raw_response": content[:500] + "..."
        }

    except Exception as e:
        print(f"LLM Error: {e}")
        # 返回 500 错误，包含具体信息方便调试
        raise HTTPException(status_code=500, detail=str(e))