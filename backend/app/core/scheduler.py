from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from ..database import SQLALCHEMY_DATABASE_URL

# 使用数据库存储 Job，防止重启丢失
jobstores = {
    'default': SQLAlchemyJobStore(url=SQLALCHEMY_DATABASE_URL)
}

scheduler = BackgroundScheduler(jobstores=jobstores, timezone="Asia/Shanghai")

def start_scheduler():
    if not scheduler.running:
        scheduler.start()
