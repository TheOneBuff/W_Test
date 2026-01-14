from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum as SqEnum
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

    # User -> LLMConfig (One-to-Many)
    llm_configs = relationship(
        "LLMConfig",
        back_populates="owner",
        primaryjoin="User.id == LLMConfig.user_id",
        foreign_keys="LLMConfig.user_id"
    )


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)

    owner_id = Column(Integer, index=True)

    create_time = Column(DateTime, default=datetime.now() + timedelta(hours=8))

    # Project -> User (Many-to-One)
    owner = relationship(
        "User",
        primaryjoin="User.id == Project.owner_id",
        foreign_keys=[owner_id]
    )

    # Project -> TestCase (One-to-Many)
    test_cases = relationship(
        "TestCase",
        back_populates="project",
        cascade="all, delete",
        primaryjoin="Project.id == TestCase.project_id",
        foreign_keys="TestCase.project_id"
    )


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)

    project_id = Column(Integer, index=True, nullable=True)

    # TestCase -> Project (Many-to-One)
    project = relationship(
        "Project",
        back_populates="test_cases",
        primaryjoin="Project.id == TestCase.project_id",
        foreign_keys=[project_id]
    )

    script_content = Column(Text, nullable=False)
    script_type = Column(String(20), default="yaml")

    create_time = Column(DateTime, default=datetime.now() + timedelta(hours=8))

    # TestCase -> TestReport (One-to-Many)
    reports = relationship(
        "TestReport",
        back_populates="test_case",
        primaryjoin="TestCase.id == TestReport.test_case_id",
        foreign_keys="TestReport.test_case_id"
    )


class TestReport(Base):
    __tablename__ = "test_reports"

    id = Column(Integer, primary_key=True, index=True)

    test_case_id = Column(Integer, index=True)

    status = Column(SqEnum(TaskStatus), default=TaskStatus.PENDING)
    start_time = Column(DateTime, default=datetime.now() + timedelta(hours=8))
    end_time = Column(DateTime, nullable=True)
    report_path = Column(String(255), nullable=True)
    logs = Column(Text, nullable=True)
    script_content = Column(Text, nullable=True)

    # TestReport -> TestCase (Many-to-One)
    test_case = relationship(
        "TestCase",
        back_populates="reports",
        primaryjoin="TestCase.id == TestReport.test_case_id",
        foreign_keys=[test_case_id]
    )


class LLMConfig(Base):
    __tablename__ = "llm_configs"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, index=True)

    name = Column(String(100), nullable=False, default="Default Config")
    is_active = Column(Boolean, default=False)

    provider = Column(String(50), default="openai")
    model_name = Column(String(100), default="gpt-4o")
    api_key = Column(String(255), nullable=True)
    base_url = Column(String(255), nullable=True)
    model_family = Column(String(50), nullable=True)
    memo = Column(String(255), nullable=True)

    # LLMConfig -> User (Many-to-One)
    owner = relationship(
        "User",
        back_populates="llm_configs",
        primaryjoin="User.id == LLMConfig.user_id",
        foreign_keys=[user_id]
    )


class Menu(Base):
    __tablename__ = "menus"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    path = Column(String(100), nullable=True)
    component = Column(String(100), nullable=True)
    icon = Column(String(50), nullable=True)
    sort = Column(Integer, default=0)

    parent_id = Column(Integer, index=True, nullable=True)

    is_hidden = Column(Boolean, default=False)

    # [修复 Menu 自关联]
    # 在没有 ForeignKey 的情况下，必须显式指定 primaryjoin
    children = relationship(
        "Menu",
        # 1. 显式指定连接条件：我的 ID 等于孩子的 parent_id
        primaryjoin="Menu.id == Menu.parent_id",

        # 2. 显式指定哪个字段是外键（虽然没物理约束，但逻辑上是）
        foreign_keys=[parent_id],

        # 3. 反向引用 (parent)
        # 注意：remote_side=[id] 告诉 ORM，在 parent 关系中，id 是“远程”那一边的（即父节点的那一边）
        backref=backref("parent", remote_side=[id])
    )


class Environment(Base):
    __tablename__ = "environments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    description = Column(String(200), nullable=True)

    project_id = Column(Integer, index=True, nullable=True)

    variables = Column(Text, nullable=False, default="{}")

    create_time = Column(DateTime, default=datetime.now() + timedelta(hours=8))


class TaskExecutionLog(Base):
    __tablename__ = "task_execution_logs"

    id = Column(Integer, primary_key=True, index=True)

    periodic_task_id = Column(Integer, index=True)

    trigger_time = Column(DateTime, default=datetime.now() + timedelta(hours=8))
    status = Column(String(20))
    report_ids = Column(Text, nullable=True)
    error_msg = Column(Text, nullable=True)

    # ExecutionLog -> PeriodicTask (Many-to-One)
    periodic_task = relationship(
        "PeriodicTask",
        backref=backref("execution_logs", foreign_keys=[periodic_task_id]),
        primaryjoin="PeriodicTask.id == TaskExecutionLog.periodic_task_id",
        foreign_keys=[periodic_task_id]
    )


class PeriodicTask(Base):
    __tablename__ = "periodic_tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    cron_expr = Column(String(50), nullable=False)

    target_type = Column(String(20), default="project")

    project_id = Column(Integer, index=True, nullable=True)
    case_ids = Column(Text, nullable=True)

    env_id = Column(Integer, index=True, nullable=True)

    is_enabled = Column(Boolean, default=True)

    create_time = Column(DateTime, default=datetime.now() + timedelta(hours=8))
    last_run_time = Column(DateTime, nullable=True)

    owner_id = Column(Integer, index=True)

    # PeriodicTask -> User (Many-to-One)
    owner = relationship(
        "User",
        primaryjoin="User.id == PeriodicTask.owner_id",
        foreign_keys=[owner_id]
    )