from fastapi import FastAPI
from .database import engine, Base
from .api import auth, user, llm, menus, testcases, projects, environments, periodic, dashboard,knowledge,vision_llm, materials, notification, skills, pc
from .tasks import run_midscene_task
from .core.scheduler import start_scheduler
from .core.logging import app_logger
Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(user.router, prefix="/api/user", tags=["user"])
app.include_router(llm.router, prefix="/api/llm", tags=["llm"])
app.include_router(menus.router, prefix="/api/menus", tags=["menus"])
app.include_router(testcases.router, prefix="/api/testcases", tags=["testcases"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(environments.router, prefix="/api/envs", tags=["envs"])
app.include_router(periodic.router, prefix="/api/periodic", tags=["periodic"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["Knowledge"])
app.include_router(vision_llm.router, prefix="/api/vision", tags=["Vision"])
app.include_router(materials.router, prefix="/api/materials", tags=["Materials"])
app.include_router(notification.router, prefix="/api/notification", tags=["Notification"])
app.include_router(skills.router, prefix="/api/skills", tags=["Skills"])
app.include_router(pc.router, prefix="/api/pc", tags=["PC Executor"])

@app.get("/")
def root(): return {"status": "ok"}

@app.on_event("startup")
def startup_event():
    # 启动调度器
    start_scheduler()