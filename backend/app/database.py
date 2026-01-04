from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:whp1148..@db/midscene_db?charset=utf8mb4"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"init_command": "SET time_zone='+08:00'"})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
