from fastapi import FastAPI
from .database import engine, Base
from .api import auth, user, llm, menus, testcases, projects, environments, periodic, dashboard,knowledge,vision_llm, materials
from .tasks import run_midscene_task # 确保 task 被注册
from .core.scheduler import start_scheduler
from .core.logging import app_logger
import subprocess
import sys
import os

app = FastAPI()
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(user.router, prefix="/api/user", tags=["user"])
app.include_router(llm.router, prefix="/api/llm", tags=["llm"]) # <--- 注册
app.include_router(menus.router, prefix="/api/menus", tags=["menus"])
app.include_router(testcases.router, prefix="/api/testcases", tags=["testcases"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(environments.router, prefix="/api/envs", tags=["envs"])
app.include_router(periodic.router, prefix="/api/periodic", tags=["periodic"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["Knowledge"])
app.include_router(vision_llm.router, prefix="/api/vision", tags=["Vision"])
app.include_router(materials.router, prefix="/api/materials", tags=["Materials"])

@app.get("/")
def root(): return {"status": "ok"}

def run_migrations():
    """运行数据库迁移"""
    app_logger.info("开始运行数据库迁移...")
    try:
        # 运行 alembic 迁移命令
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        
        if result.returncode == 0:
            app_logger.info("数据库迁移成功完成！")
            app_logger.info(f"迁移输出: {result.stdout}")
        else:
            app_logger.error("数据库迁移失败！")
            app_logger.error(f"错误信息: {result.stderr}")
    except Exception as e:
        app_logger.error(f"运行迁移时发生错误: {e}")

@app.on_event("startup")
def startup_event():
    # 首先运行数据库迁移
    run_migrations()
    # 然后启动调度器
    start_scheduler()