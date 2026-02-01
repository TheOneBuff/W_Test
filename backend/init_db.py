from app.database import SessionLocal, engine
from app.models import Base, User, Menu
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
        # 仅在菜单表为空时执行初始化
        if db.query(Menu).count() == 0:
            print("Initializing Menus...")

            # --- A. 根菜单 (无子菜单) ---
            db.add(Menu(title="控制台", path="/", icon="Odometer", sort=1, component="Dashboard"))
            db.add(Menu(title="项目管理", path="/projects", icon="Folder", sort=3, component="ProjectList"))

            # --- AI 模块 ---
            db.add(Menu(title="知识库管理", path="/knowledge", icon="Files", sort=6, component="KnowledgeBase"))
            db.add(Menu(title="智能用例生成", path="/generator", icon="MagicStick", sort=7, component="CaseGenerator"))

            # [新增] AI 视觉找茬
            # 路径 /tools/ai-diff 对应前端路由配置
            # 组件 AiDiff 对应前端 views/AiDiff.vue
            db.add(Menu(title="AI 视觉找茬", path="/tools/ai-diff", icon="View", sort=8, component="AiDiff"))

            # --- B. 父菜单 ---

            # WEB_UI (将 sort 顺延到 10，避免冲突)
            m_web_ui = Menu(title="WEB_UI", icon="Monitor", sort=10)
            db.add(m_web_ui)

            m_system = Menu(title="系统管理", icon="Setting", sort=99)
            db.add(m_system)

            db.flush()  # 提交以获取 ID

            # 1. WEB_UI 子菜单
            if m_web_ui.id:
                db.add(Menu(title="测试报告", path="/reports", icon="DataAnalysis", parent_id=m_web_ui.id, sort=1,
                            component="ReportList"))
                db.add(Menu(title="WEB_UI用例管理", path="/testcases", icon="List", parent_id=m_web_ui.id, sort=2,
                            component="TestCaseList"))

            # 2. 系统管理 子菜单
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

            db.commit()
            print("Menus initialized successfully.")
        else:
            print("Menus table is not empty, skipping initialization.")
    except Exception as e:
        print(f"Error initializing menus: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init()