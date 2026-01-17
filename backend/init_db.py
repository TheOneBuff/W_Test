from app.database import SessionLocal, engine
from app.models import Base, User, Menu
from app.core.security import get_password_hash


def init():
    # 创建表结构
    Base.metadata.create_all(bind=engine)

    # 1. 初始化管理员
    db = SessionLocal()
    if not db.query(User).filter_by(username="admin").first():
        user = User(username="admin", hashed_password=get_password_hash("123456"))
        db.add(user)
        db.commit()
        print("Admin user created: admin / 123456")
    db.close()

    # 2. 初始化菜单
    db = SessionLocal()
    # 注意：这里仅在菜单表为空时执行初始化
    # 如果您已经运行过项目，需要清空 menus 表或者手动删除数据，才能触发此逻辑
    if db.query(Menu).count() == 0:
        print("Initializing Menus...")

        # --- 根菜单 ---
        # 1. 控制台
        db.add(Menu(title="控制台", path="/", icon="Odometer", sort=1, component="Dashboard"))

        # 2. 系统管理 (父菜单，稍后添加子菜单)
        m_system = Menu(title="系统管理", icon="Setting", sort=99)  # 放到最后，或者设为 2
        db.add(m_system)

        # 3. 业务菜单
        db.add(Menu(title="项目管理", path="/projects", icon="Folder", sort=3, component="ProjectList"))
        db.add(Menu(title="测试报告", path="/reports", icon="DataAnalysis", sort=4, component="ReportList"))
        db.add(Menu(title="用例管理", path="/testcases", icon="List", sort=5, component="TestCaseList"))

        # === [新增] AI 能力模块 ===
        db.add(Menu(title="知识库管理", path="/knowledge", icon="Files", sort=6, component="KnowledgeBase"))
        db.add(Menu(title="智能用例生成", path="/generator", icon="MagicStick", sort=7, component="CaseGenerator"))
        # =======================

        db.flush()  # 提交并获取自增 ID，主要用于 m_system.id

        # --- 系统管理子菜单 ---
        # 使用 m_system.id 作为父ID
        if m_system.id:
            db.add(Menu(title="用户管理", path="/users", icon="User", sort=1, parent_id=m_system.id,
                        component="UserManage"))
            db.add(Menu(title="菜单管理", path="/menus", icon="Menu", sort=2, parent_id=m_system.id,
                        component="MenuManage"))
            db.add(
                Menu(title="大模型配置", path="/llm", icon="Cpu", sort=3, parent_id=m_system.id, component="LLMConfig"))
            db.add(Menu(title="环境管理", path="/envs", icon="Connection", sort=4, parent_id=m_system.id,
                        component="EnvManage"))
            db.add(Menu(title="定时任务", path="/periodic", icon="AlarmClock", sort=5, parent_id=m_system.id,
                        component="ScheduledTasks"))

        db.commit()
        print("Menus initialized successfully.")
    else:
        print("Menus table is not empty, skipping initialization.")

    db.close()


if __name__ == "__main__":
    init()