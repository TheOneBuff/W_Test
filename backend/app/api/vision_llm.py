from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
import base64
import json
import io
import re
import hashlib
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageOps, ImageFont
from openai import OpenAI
from skimage.metrics import structural_similarity as ssim
import easyocr
from difflib import SequenceMatcher

router = APIRouter()

# 初始化 OCR Reader
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)


# --- 辅助函数区域 ---

def calculate_md5(file_bytes):
    return hashlib.md5(file_bytes).hexdigest()


def calculate_ssim(img_bytes1, img_bytes2):
    try:
        nparr1 = np.frombuffer(img_bytes1, np.uint8)
        nparr2 = np.frombuffer(img_bytes2, np.uint8)
        img1 = cv2.imdecode(nparr1, cv2.IMREAD_GRAYSCALE)
        img2 = cv2.imdecode(nparr2, cv2.IMREAD_GRAYSCALE)
        if img1 is None or img2 is None: return 0.0
        if img1.shape != img2.shape:
            img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
        score, _ = ssim(img1, img2, full=True)
        return score
    except:
        return 0.0


def compress_image(image_bytes, max_size=2048):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        width, height = img.size
        if max(width, height) > max_size:
            scale = max_size / max(width, height)
            img = img.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=90)
        return buffered.getvalue()
    except:
        return image_bytes


def get_text_similarity(str1, str2):
    return SequenceMatcher(None, str1, str2).ratio()


def verify_diff_with_ocr(img1_bytes, img2_bytes, diffs):
    """OCR 双重验证"""
    if not diffs: return []
    img1 = Image.open(io.BytesIO(img1_bytes))
    img2 = Image.open(io.BytesIO(img2_bytes))
    w, h = img2.size
    verified_diffs = []

    print(f">> 开始 OCR 验证，待查数量: {len(diffs)}")

    # [安全锁] 如果 AI 返回了超过 20 个差异，强制只验证前 20 个，防止 OCR 跑死
    target_diffs = diffs[:20]

    for item in target_diffs:
        box = item.get("box", [])
        if len(box) != 4: continue
        x1 = int(box[0] / 1000 * w)
        y1 = int(box[1] / 1000 * h)
        x2 = int(box[2] / 1000 * w)
        y2 = int(box[3] / 1000 * h)

        if x2 - x1 < 5 or y2 - y1 < 5: continue

        try:
            crop1 = img1.crop((x1, y1, x2, y2))
            crop2 = img2.crop((x1, y1, x2, y2))
            res1 = reader.readtext(np.array(crop1), detail=0)
            res2 = reader.readtext(np.array(crop2), detail=0)
            text1 = "".join(res1).replace(" ", "").strip()
            text2 = "".join(res2).replace(" ", "").strip()

            # 验证逻辑
            if text1 and text2:
                if text1 == text2: continue  # 完全相同，剔除
                if get_text_similarity(text1, text2) > 0.9: continue  # 高度相似，剔除

            verified_diffs.append(item)
        except Exception as e:
            print(f"OCR Error for box {box}: {e}")
            continue

    return verified_diffs


def clean_diffs_logic(diffs):
    """逻辑清洗 + 垃圾数据熔断"""
    valid_diffs = []
    unique_reasons = set()

    # 1. 熔断机制：如果 AI 疯了返回了几百个差异，直接截断
    if len(diffs) > 30:
        print(f">> 检测到 AI 死循环 (返回 {len(diffs)} 条)，触发熔断，仅保留前 15 条")
        diffs = diffs[:15]

    for item in diffs:
        reason = item.get("reason", "").strip()

        # 2. 过滤垃圾 reason
        if not reason or reason in ["文字内容 different", "文字 content different", "文字内容不同", "不同"]:
            continue  # 丢弃这种毫无意义的复读机描述

        # 3. 过滤重复 reason (防止满屏都是 "标签错误")
        if reason in unique_reasons:
            continue
        unique_reasons.add(reason)

        # 4. 正则自检
        if "相同" in reason or "一致" in reason: continue
        match = re.search(r"预期为['\"](.*?)['\"]，?.*实际为['\"](.*?)['\"]", reason)
        if match and match.group(1) == match.group(2): continue

        valid_diffs.append(item)

    return valid_diffs


def draw_boxes(image_bytes, diffs):
    img = Image.open(io.BytesIO(image_bytes))
    draw = ImageDraw.Draw(img)
    width, height = img.size

    font = None
    try:
        font_paths = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "arial.ttf"]
        for path in font_paths:
            try:
                font = ImageFont.truetype(path, 24); break
            except:
                continue
    except:
        pass

    for idx, item in enumerate(diffs, 1):
        box = item.get("box", [])
        if len(box) == 4:
            # 坐标映射 + 越界保护
            x1 = max(0, int(min(box[0], box[2]) / 1000 * width))
            y1 = max(0, int(min(box[1], box[3]) / 1000 * height))
            x2 = min(width, int(max(box[0], box[2]) / 1000 * width))
            y2 = min(height, int(max(box[1], box[3]) / 1000 * height))

            draw.rectangle([x1, y1, x2, y2], outline="#ff0000", width=4)
            draw.rectangle([x1, y1 - 25, x1 + 30, y1], fill="#ff0000")
            draw.text((x1 + 5, y1 - 25), str(idx), fill="white", font=font)

    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    return f"data:image/jpeg;base64,{base64.b64encode(buffered.getvalue()).decode('utf-8')}"


def try_repair_json(json_str):
    """暴力修复 JSON，截断尾部垃圾"""
    # 如果包含大量重复，直接截断到合理的长度
    json_str = json_str.strip()

    # 尝试找到最后关闭的 diffs 数组
    end_idx = json_str.rfind("}]")
    if end_idx != -1:
        json_str = json_str[:end_idx + 2] + "}"
    else:
        # 如果彻底烂了，尝试补全
        if not json_str.endswith("}"):
            if json_str.rfind("]") < json_str.rfind("["):
                json_str += "]}"
            elif json_str.endswith(","):
                json_str = json_str[:-1] + "]}"
            else:
                json_str += "}"

    try:
        return json.loads(json_str)
    except:
        try:
            pattern = r'\{\s*"box":\s*\[\d+,\s*\d+,\s*\d+,\s*\d+\],\s*"reason":\s*".*?"\s*\}'
            matches = re.findall(pattern, json_str)
            # 熔断：如果匹配到太多，只取前 15 个
            if len(matches) > 15: matches = matches[:15]
            if matches:
                valid_items = ",".join(matches)
                return json.loads(f'{{"diffs": [{valid_items}]}}')
        except:
            return {"diffs": []}
    return {"diffs": []}


# --- 核心接口 ---

@router.post("/ai-diff")
async def ai_ui_diff(
        file1: UploadFile = File(...),
        file2: UploadFile = File(...),
        prompt_hint: str = Form(default="找出所有key不一致的地方"),
        db: Session = Depends(get_db)
):
    f1_bytes = await file1.read()
    f2_bytes = await file2.read()

    # 1. MD5
    if calculate_md5(f1_bytes) == calculate_md5(f2_bytes):
        return {"diff_count": 0, "result_image": f"data:image/jpeg;base64,{base64.b64encode(f2_bytes).decode('utf-8')}",
                "details": []}

    # 2. SSIM
    sim_score = calculate_ssim(f1_bytes, f2_bytes)
    if sim_score > 0.995:
        return {"diff_count": 0, "result_image": f"data:image/jpeg;base64,{base64.b64encode(f2_bytes).decode('utf-8')}",
                "details": []}

    # 3. LLM Config
    llm_config = db.query(models.LLMConfig).filter(models.LLMConfig.is_active_gen == True).first()
    if not llm_config: raise HTTPException(status_code=400, detail="未配置 LLM")

    # 4. 压缩
    opt_f1 = compress_image(f1_bytes, 2048)
    opt_f2 = compress_image(f2_bytes, 2048)
    # 对齐尺寸
    img1_pil = Image.open(io.BytesIO(opt_f1))
    img2_pil = Image.open(io.BytesIO(opt_f2))
    if img1_pil.size != img2_pil.size:
        img1_pil = img1_pil.resize(img2_pil.size)
        buf = io.BytesIO();
        img1_pil.save(buf, format="JPEG");
        opt_f1 = buf.getvalue()

    b64_1 = base64.b64encode(opt_f1).decode('utf-8')
    b64_2 = base64.b64encode(opt_f2).decode('utf-8')

    # 5. Prompt (增强防御)
    system_prompt = """
    你是一个严谨的UI测试专家。对比两张图。
    【严重警告】
    1. **数量限制**：最多只返回 **10个** 最重要的差异！绝对不要超过10个！
    2. **禁止复读**：严禁连续输出 "文字内容不同" 这种废话。必须说明具体差异（如 "预期'登录'，实际'注册'"）。
    3. **列表去重**：如果列表每一行都有错，**只报第一行**，并注明 "其余行同理"。

    【输出格式】
    {"diffs": [{"box": [xmin, ymin, xmax, ymax], "reason": "具体差异描述"}]}
    """
    user_msg = f"指令: {prompt_hint}。请返回JSON。"

    client = OpenAI(api_key=llm_config.api_key, base_url=llm_config.base_url)
    try:
        resp = client.chat.completions.create(
            model=llm_config.model_name or "gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": user_msg},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_1}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_2}"}}
                ]}
            ],
            max_tokens=4096,  # 恢复限制，防止死循环跑太久
            temperature=0.1,  # 稍微增加一点随机性打破死循环
            frequency_penalty=1.0,  # [关键] 强力惩罚重复词
            presence_penalty=1.0  # [关键] 鼓励生成新内容
        )
        content = resp.choices[0].message.content
        print(f">> LLM Res: {content[:500]}...")  # 只打印前500字看日志

        cleaned = re.sub(r"```json|```", "", content).strip()
        data = try_repair_json(cleaned)
        raw_diffs = data.get("diffs", [])

        # 6. 强力清洗 & OCR 验证
        logic_filtered = clean_diffs_logic(raw_diffs)
        final_diffs = verify_diff_with_ocr(opt_f1, opt_f2, logic_filtered)

        print(f"原始: {len(raw_diffs)} -> 逻辑清洗: {len(logic_filtered)} -> OCR验证: {len(final_diffs)}")

        result_b64 = draw_boxes(opt_f2, final_diffs) if final_diffs else f"data:image/jpeg;base64,{b64_2}"

        return {
            "diff_count": len(final_diffs),
            "result_image": result_b64,
            "details": final_diffs,
            "raw_response": content[:200] + "..."  # 缩略返回，防止前端炸裂
        }

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))