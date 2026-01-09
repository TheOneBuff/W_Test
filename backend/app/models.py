from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SqEnum, Boolean
from sqlalchemy.orm import relationship, backref
from datetime import datetime, timedelta
import enum

from .database import Base


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(100), nullable=False)

    # 关系定义
    # llm_config 通过 User.llm_config = relationship(...) 后置定义


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    create_time = Column(DateTime, default=datetime.now() + timedelta(hours=8))  # 使用本地时间

    owner = relationship("User")
    # 关联用例
    test_cases = relationship("TestCase", back_populates="project", cascade="all, delete")


# --- 核心补充: TestCase ---
class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    project = relationship("Project", back_populates="test_cases")

    # 核心脚本字段
    script_content = Column(Text, nullable=False)
    script_type = Column(String(20), default="yaml")  # yaml / prompt

    create_time = Column(DateTime, default=datetime.now() + timedelta(hours=8))

    # 关联
    reports = relationship("TestReport", back_populates="test_case")


# --- TestReport ---
class TestReport(Base):
    __tablename__ = "test_reports"

    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id"))

    status = Column(SqEnum(TaskStatus), default=TaskStatus.PENDING)
    start_time = Column(DateTime, default=datetime.now() + timedelta(hours=8))
    end_time = Column(DateTime, nullable=True)
    report_path = Column(String(255), nullable=True)
    logs = Column(Text, nullable=True)
    # 快照，可选
    script_content = Column(Text, nullable=True)

    test_case = relationship("TestCase", back_populates="reports")


# --- LLMConfig ---
class LLMConfig(Base):
    __tablename__ = "llm_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    provider = Column(String(50), default="openai")
    model_name = Column(String(100), default="gpt-4o")
    api_key = Column(String(255), nullable=True)
    base_url = Column(String(255), nullable=True)
    model_family = Column(String(50), nullable=True)
    memo = Column(String(255), nullable=True)
    owner = relationship("User", back_populates="llm_config")


# --- Menu ---
class Menu(Base):
    __tablename__ = "menus"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    path = Column(String(100), nullable=True)
    component = Column(String(100), nullable=True)
    icon = Column(String(50), nullable=True)
    sort = Column(Integer, default=0)
    parent_id = Column(Integer, ForeignKey("menus.id"), nullable=True)
    is_hidden = Column(Boolean, default=False) if 'Boolean' in locals() else Column(Integer,
                                                                                    default=0)  # 修正: 确保 Boolean 导入或用 Integer

    children = relationship("Menu", backref=backref("parent", remote_side=[id]))


class Environment(Base):
    __tablename__ = "environments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)  # 例如 "Test Env"
    description = Column(String(200), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)  # 可选：绑定项目

    # 存储变量 (JSON 格式)
    # 例如: {"BASE_URL": "http://localhost", "USER": "admin"}
    variables = Column(Text, nullable=False, default="{}")

    create_time = Column(DateTime, default=datetime.now() + timedelta(hours=8))

    # 关联项目 (可选)
    # project = relationship("Project", backref="environments")


class TaskExecutionLog(Base):
    __tablename__ = "task_execution_logs"

    id = Column(Integer, primary_key=True, index=True)
    periodic_task_id = Column(Integer, ForeignKey("periodic_tasks.id"))

    trigger_time = Column(DateTime, default=datetime.now() + timedelta(hours=8))
    status = Column(String(20))  # "success", "failed", "partial"

    # 记录生成的报告ID列表 (JSON 数组, e.g. "[101, 102]")
    report_ids = Column(Text, nullable=True)
    error_msg = Column(Text, nullable=True)

    # 关联
    periodic_task = relationship("PeriodicTask", backref="execution_logs")


class PeriodicTask(Base):
    __tablename__ = "periodic_tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    cron_expr = Column(String(50), nullable=False)

    target_type = Column(String(20), default="project")  # "project" / "cases"
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    case_ids = Column(Text, nullable=True)

    env_id = Column(Integer, ForeignKey("environments.id"), nullable=True)
    is_enabled = Column(Boolean, default=True) if 'Boolean' in locals() else Column(Integer, default=1)

    create_time = Column(DateTime, default=datetime.now() +timedelta(hours=8))
    last_run_time = Column(DateTime, nullable=True)

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User")

# 后置绑定
User.llm_config = relationship("LLMConfig", back_populates="owner", uselist=False)


