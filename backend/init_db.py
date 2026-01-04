from app.database import SessionLocal, engine
from app.models import Base, User
from app.core.security import get_password_hash
from app.models import Menu

def init():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if not db.query(User).filter_by(username="admin").first():
        user = User(username="admin", hashed_password=get_password_hash("123456"))
        db.add(user)
        db.commit()
        print("Admin user created: admin / 123456")
    # 初始化菜单
    db = SessionLocal()
    if db.query(Menu).count() == 0:
        print("Initializing Menus...")
        # 1. 控制台
        m1 = Menu(title="控制台", path="/", icon="Odometer", sort=1, component="Dashboard")
        db.add(m1)

        db.add(Menu(title="用例管理", path="/testcases", icon="List", sort=5, component="TestCaseList"))
        db.add(Menu(title="项目管理", path="/projects", icon="Folder", sort=3, component="ProjectList"))
        db.add(Menu(title="测试报告", path="/reports", icon="DataAnalysis", sort=4, component="ReportList"))


        # 2. 系统管理 (父菜单)
        m2 = Menu(title="系统管理", icon="Setting", sort=2)
        db.add(m2)
        db.flush()  # 获取 m2.id



        # 2.1 用户管理
        m2_1 = Menu(title="用户管理", path="/users", icon="User", sort=1, parent_id=m2.id, component="UserManage")
        db.add(m2_1)

        # 2.2 菜单管理 (自己)
        m2_2 = Menu(title="菜单管理", path="/menus", icon="Menu", sort=2, parent_id=m2.id, component="MenuManage")
        db.add(m2_2)

        # 2.3 LLM 配置
        m2_3 = Menu(title="大模型配置", path="/llm", icon="Cpu", sort=3, parent_id=m2.id, component="LLMConfig")
        db.add(m2_3)

        m2_4 = Menu(title="环境管理", path="/envs", icon="Connection", sort=4, parent_id=m2.id, component="EnvManage")
        db.add(m2_4)

        m2_5 = Menu(title="定时任务", path="/periodic", icon="AlarmClock", sort=5, parent_id=m2.id, component="ScheduledTasks")
        db.add(m2_5)

        db.commit()
        print("Menus initialized.")
    db.close()

if __name__ == "__main__":
    init()
