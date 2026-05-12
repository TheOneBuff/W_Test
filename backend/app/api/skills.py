from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import models, schemas
from ..database import get_db
from .auth import get_current_user

router = APIRouter()


@router.get("/", response_model=List[schemas.SkillOut])
def get_skills(
        skip: int = 0,
        limit: int = 100,
        skill_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.Skill)

    if skill_type:
        query = query.filter(models.Skill.skill_type == skill_type)
    if is_active is not None:
        query = query.filter(models.Skill.is_active == is_active)

    skills = query.order_by(models.Skill.create_time.desc()).offset(skip).limit(limit).all()
    return skills


@router.get("/available")
def get_available_skills(
        has_image: bool = False,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.Skill).filter(models.Skill.is_active == True)

    if has_image:
        query = query.filter(models.Skill.skill_type.in_(["general", "image"]))

    skills = query.order_by(models.Skill.create_time.desc()).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "skill_type": s.skill_type
        }
        for s in skills
    ]


@router.get("/{skill_id}", response_model=schemas.SkillOut)
def get_skill(
        skill_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    skill = db.query(models.Skill).filter(models.Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    return skill


@router.post("/", response_model=schemas.SkillOut)
def create_skill(
        skill_data: schemas.SkillCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    db_skill = models.Skill(
        name=skill_data.name,
        description=skill_data.description,
        prompt_content=skill_data.prompt_content,
        skill_type=skill_data.skill_type,
        is_active=skill_data.is_active,
        created_by=current_user.id
    )
    db.add(db_skill)
    db.commit()
    db.refresh(db_skill)
    return db_skill


@router.put("/{skill_id}", response_model=schemas.SkillOut)
def update_skill(
        skill_id: int,
        skill_data: schemas.SkillUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    skill = db.query(models.Skill).filter(models.Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    update_data = skill_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(skill, field, value)

    db.commit()
    db.refresh(skill)
    return skill


@router.delete("/{skill_id}")
def delete_skill(
        skill_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    skill = db.query(models.Skill).filter(models.Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    db.delete(skill)
    db.commit()
    return {"status": "success"}


@router.post("/{skill_id}/toggle")
def toggle_skill(
        skill_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    skill = db.query(models.Skill).filter(models.Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    skill.is_active = not skill.is_active
    db.commit()
    db.refresh(skill)
    return {"status": "success", "is_active": skill.is_active}


@router.post("/seed-defaults")
def seed_default_skills(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    existing_skills = db.query(models.Skill).count()
    if existing_skills > 0:
        return {"status": "skipped", "message": "默认技能已存在"}

    default_skills = [
        {
            "name": "通用用例生成",
            "description": "通用的测试用例生成技能，适用于大多数应用场景",
            "skill_type": "general",
            "prompt_content": """
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
        },
        {
            "name": "UI截图用例生成",
            "description": "根据UI截图生成测试用例，适用于界面设计验证",
            "skill_type": "image",
            "prompt_content": """
你是一个资深的UI/UX测试专家。你需要根据用户的【图片】设计一条测试用例。
!!! 核心要求 (CRITICAL INSTRUCTION) !!!
1. **严格遵守参考风格**：输出格式必须严格模仿下方的风格（包括字段排版、分割线风格、JSON 键值结构）
    参考风格：
—————————————————————————————————————————
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
——————————————————————————————————————————
2. **视觉还原**：多行文本或特殊符号来模拟 UI 布局，请照做，尽量还原视觉
3. **详细度**：不要只写"显示正确"，要写出具体的字段值。
请输出纯 JSON 格式的列表，列表项包含：module, title, precondition, steps (数组), expected, priority (P0/P1/P2)。
"""
        }
    ]

    for skill_data in default_skills:
        db_skill = models.Skill(
            name=skill_data["name"],
            description=skill_data["description"],
            prompt_content=skill_data["prompt_content"],
            skill_type=skill_data["skill_type"],
            is_active=True,
            created_by=current_user.id
        )
        db.add(db_skill)

    db.commit()
    return {"status": "success", "message": f"已创建 {len(default_skills)} 个默认技能"}
