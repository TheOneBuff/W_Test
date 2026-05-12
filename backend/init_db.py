from app.database import SessionLocal, engine
from app.models import Base, User, Menu, TestRule, RuleSet, RuleSetMapping
from app.core.security import get_password_hash


def init():
    # 创建表结构
    Base.metadata.create_all(bind=engine)

    # 1. 初始化管理员
    db = SessionLocal()
    try:
        if not db.query(User).filter_by(username="admin").first():
            user = User(username="admin", hashed_password=get_password_hash("123456"))
            db.add(user)
            db.commit()
            print("Admin user created: admin / 123456")
    finally:
        db.close()

    # 2. 初始化菜单
    db = SessionLocal()
    try:
        if db.query(Menu).count() == 0:
            print("Initializing Menus...")

            db.add(Menu(title="控制台", path="/", icon="Odometer", sort=1, component="Dashboard"))
            db.add(Menu(title="项目管理", path="/projects", icon="Folder", sort=3, component="ProjectList"))

            db.add(Menu(title="知识库管理", path="/knowledge", icon="Files", sort=6, component="KnowledgeBase"))
            db.add(Menu(title="智能用例生成", path="/generator", icon="MagicStick", sort=7, component="CaseGenerator"))

            db.add(Menu(title="AI 视觉找茬", path="/tools/ai-diff", icon="View", sort=8, component="AiDiff"))

            m_web_ui = Menu(title="AI自动化", icon="Monitor", sort=10)
            db.add(m_web_ui)

            m_system = Menu(title="系统管理", icon="Setting", sort=99)
            db.add(m_system)

            db.flush()

            if m_web_ui.id:
                db.add(Menu(title="测试报告", path="/reports", icon="DataAnalysis", parent_id=m_web_ui.id, sort=1,
                            component="ReportList"))
                db.add(Menu(title="用例管理", path="/testcases", icon="List", parent_id=m_web_ui.id, sort=2,
                            component="TestCaseList"))
                db.add(Menu(title="素材管理", path="/materials", icon="Picture", parent_id=m_web_ui.id, sort=3,
                            component="MaterialUpload"))

            if m_system.id:
                db.add(Menu(title="用户管理", path="/users", icon="User", sort=1, parent_id=m_system.id,
                            component="UserManage"))
                db.add(Menu(title="菜单管理", path="/menus", icon="Menu", sort=2, parent_id=m_system.id,
                            component="MenuManage"))
                db.add(Menu(title="大模型配置", path="/llm", icon="Cpu", sort=3, parent_id=m_system.id,
                            component="LLMConfig"))
                db.add(Menu(title="环境管理", path="/envs", icon="Connection", sort=4, parent_id=m_system.id,
                            component="EnvManage"))
                db.add(Menu(title="定时任务", path="/periodic", icon="AlarmClock", sort=5, parent_id=m_system.id,
                            component="ScheduledTasks"))
                db.add(Menu(title="通知管理", path="/notifications", icon="Bell", sort=6, parent_id=m_system.id,
                            component="NotificationManage"))
                db.add(Menu(title="技能管理", path="/skills", icon="Grid", sort=7, parent_id=m_system.id,
                            component="SkillManage"))
                db.add(Menu(title="执行器管理", path="/executors", icon="Cpu", sort=8, parent_id=m_system.id,
                            component="ExecutorManage"))
                db.add(Menu(title="规则管理", path="/rules", icon="Document", sort=9, parent_id=m_system.id,
                            component="RuleManage"))

            db.commit()
            print("Menus initialized successfully.")
        else:
            print("Menus table is not empty, skipping initialization.")
    except Exception as e:
        print(f"Error initializing menus: {e}")
        db.rollback()
    finally:
        db.close()

    # 3. 初始化默认测试规则
    db = SessionLocal()
    try:
        if db.query(TestRule).count() == 0:
            print("Seeding default test rules...")
            seed_rules(db)
            print("Default test rules seeded successfully.")
        else:
            print("Test rules table is not empty, skipping.")
    except Exception as e:
        print(f"Error seeding rules: {e}")
        db.rollback()
    finally:
        db.close()


def seed_rules(db):
    default_rules = [
        {
            "name": "金额边界值规则",
            "description": "金额输入框的有效范围边界测试",
            "rule_content": "金额输入框的有效值范围为 0.01 ~ 99999.99。必须测试的边界值：0、0.01、99999.99、100000、-1、负数、非数字字符、科学计数法。",
            "rule_type": "boundary",
            "tags": ["金额", "边界值", "输入框"],
            "priority": "P0",
            "condition_expr": "amount >= 0.01 AND amount <= 99999.99",
            "example": "正例: 输入0.01应接受；反例: 输入0应提示'金额不能为0'；输入100000应提示'超出最大限额'"
        },
        {
            "name": "字符串长度边界规则",
            "description": "输入框字符长度限制测试",
            "rule_content": "任何有长度限制的输入框，需测试：空字符串(0)、1个字符、最大长度-1、最大长度、最大长度+1、超长字符串(1000+字符)、特殊Unicode字符(emoji等)。",
            "rule_type": "boundary",
            "tags": ["边界值", "字符串", "输入框", "长度"],
            "priority": "P1",
            "example": "若最大长度为50，测试: ''(空), 'a'(1字符), 49字符, 50字符, 51字符"
        },
        {
            "name": "分页边界规则",
            "description": "分页组件的边界条件测试",
            "rule_content": "分页需测试：首页(第1页)、末页(最后一页)、页码0、负数页码、超大页码(999999)、非数字页码、上一页/下一页在边界时的行为。",
            "rule_type": "boundary",
            "tags": ["分页", "边界值", "列表"],
            "priority": "P1",
            "example": "总数据0条时分页组件应隐藏；总数据1条时只显示1页"
        },
        {
            "name": "必填项校验规则",
            "description": "所有必填字段的校验测试",
            "rule_content": "所有标记为必填(带*号)的字段，提交时应验证：全空提交、部分填写提交、仅空格提交、特殊字符(如<script>alert(1)</script>)提交。系统应给出明确错误提示，且不应丢失已填写的数据。",
            "rule_type": "constraint",
            "tags": ["必填项", "校验", "表单"],
            "priority": "P0",
            "example": "用户注册表单，留空所有必填项点击提交，应提示'请填写XXX'并高亮空字段"
        },
        {
            "name": "数据格式校验规则",
            "description": "邮箱/手机号/身份证等格式校验",
            "rule_content": "对特定格式字段需要：有效格式测试、无效格式测试、边界格式测试。邮箱: test@example.com(有效)、test@(无效)、超长邮箱。手机号: 13800138000(有效)、12345(无效)、含字母。身份证: 18位有效、15位、17位、含X的、含特殊字符的。",
            "rule_type": "constraint",
            "tags": ["格式校验", "邮箱", "手机号", "身份证"],
            "priority": "P1",
            "example": "邮箱输入框输入'test@'，应提示'请输入有效的邮箱地址'"
        },
        {
            "name": "订单状态流转规则",
            "description": "验证订单各状态间的正确流转",
            "rule_content": "标准订单状态流转: 待支付→已支付→已发货→已完成。不允许跨状态跳转(如待支付→已完成)，不允许逆向流转(如已完成→已支付)。取消订单只允许在待支付和已支付状态。",
            "rule_type": "biz_rule",
            "tags": ["订单", "状态迁移", "业务规则"],
            "priority": "P0",
            "example": "已发货的订单尝试取消，应提示'当前状态不允许取消'"
        },
        {
            "name": "敏感操作二次验证",
            "description": "涉及资金/密码的操作需二次验证",
            "rule_content": "所有涉及资金变动、密码修改、权限变更的操作，必须经过二次身份验证(短信验证码/邮箱验证码/密码确认)。验证码有效期5分钟，错误超过3次锁定30分钟。",
            "rule_type": "security",
            "tags": ["安全", "验证", "资金", "密码"],
            "priority": "P0",
            "example": "修改支付密码：先输入原密码验证 → 发送短信验证码 → 输入新密码 → 确认新密码"
        },
        {
            "name": "SQL注入/XSS防护规则",
            "description": "所有输入点需测试脚本注入",
            "rule_content": "所有文本输入框需测试：SQL注入('<script>alert(1)</script>')、XSS('<img src=x onerror=alert(1)>')、SQL片段('1' OR '1'='1')、HTML标签注入、JSON注入。提交后页面不应执行注入代码，数据库不应被破坏。",
            "rule_type": "security",
            "tags": ["安全", "SQL注入", "XSS", "输入框"],
            "priority": "P0",
            "example": "搜索框输入'<script>alert('XSS')</script>'，搜索结果页不应弹窗"
        },
        {
            "name": "等价类划分规则",
            "description": "使用等价类方法减少冗余测试",
            "rule_content": "对输入域划分有效等价类和无效等价类。每个有效等价类至少设计1个正向用例，每个无效等价类至少设计1个逆向用例。典型等价类：数值范围(有效区间/无效区间)、必填/非必填、合法字符集/非法字符集。",
            "rule_type": "equivalence",
            "tags": ["等价类", "测试方法", "用例设计"],
            "priority": "P1",
            "example": "年龄输入框(1-120)：有效等价类[1,50,120]，无效等价类[0, -1, 121, 'abc']"
        },
        {
            "name": "并发/重复提交规则",
            "description": "防止重复提交和并发冲突",
            "rule_content": "提交按钮点击后应立即禁用(loading状态)，防止重复提交。短时间内多次点击只应产生一次有效请求。网络超时重试不应产生重复数据。涉及库存/余额的操作需验证并发场景下的数据一致性。",
            "rule_type": "data_rule",
            "tags": ["并发", "重复提交", "幂等性", "数据一致性"],
            "priority": "P1",
            "example": "快速双击'提交订单'按钮，只应生成一个订单"
        },
    ]

    rule_objects = []
    for r in default_rules:
        rule = TestRule(
            name=r["name"],
            description=r["description"],
            rule_content=r["rule_content"],
            rule_type=r["rule_type"],
            scope_type="global",
            priority=r["priority"],
            tags=r.get("tags"),
            condition_expr=r.get("condition_expr"),
            example=r.get("example"),
            is_active=True,
            created_by=None
        )
        db.add(rule)
        rule_objects.append(rule)

    db.flush()

    if rule_objects:
        default_set = RuleSet(
            name="默认规则集",
            description="系统预置的通用测试规则集，适用于所有项目",
            set_type="default",
            is_active=True,
            is_default=True,
            created_by=None
        )
        db.add(default_set)
        db.flush()

        for idx, rule in enumerate(rule_objects):
            mapping = RuleSetMapping(
                rule_set_id=default_set.id,
                rule_id=rule.id,
                sort_order=idx
            )
            db.add(mapping)

    db.commit()
    print(f"Seeded {len(rule_objects)} rules and 1 default rule set.")


if __name__ == "__main__":
    init()