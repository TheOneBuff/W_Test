from fastapi import FastAPI
from .database import engine, Base
from .api import auth, user, llm, menus, testcases, projects, environments, periodic, dashboard,knowledge,vision_llm
from .tasks import run_midscene_task # 确保 task 被注册
from .core.scheduler import start_scheduler

Base.metadata.create_all(bind=engine)

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
@app.get("/")
def root(): return {"status": "ok"}

@app.on_event("startup")
def startup_event():
    start_scheduler()