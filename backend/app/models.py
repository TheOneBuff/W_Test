from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum as SqEnum, JSON
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

    create_time = Column(DateTime, default=datetime.now())

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

    create_time = Column(DateTime, default=datetime.now())

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
    batch_id = Column(String(50), index=True, nullable=True)  # 批量运行批次ID

    status = Column(SqEnum(TaskStatus), default=TaskStatus.PENDING)
    start_time = Column(DateTime, default=datetime.now())
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

    is_active_chat = Column(Boolean, default=False)  # 向量对话
    is_active_gen = Column(Boolean, default=False)  # 用例生成
    is_active_exec = Column(Boolean, default=False)  # 用例执行

    # 2. 基础信息
    provider = Column(String(50), default="openai")
    model_name = Column(String(100), default="gpt-4o")
    api_key = Column(String(255), nullable=True)
    base_url = Column(String(255), nullable=True)

    # model_type 保留，用于区分视觉/文本模型
    model_type = Column(String(20), default="text", nullable=False)
    model_family = Column(String(50), nullable=True)
    memo = Column(String(255), nullable=True)

    # 3. [修复报错的关键] 添加时间字段
    created_at = Column(DateTime, default=datetime.now())
    updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now())

    owner = relationship(
        "User",
        back_populates="llm_configs",
        primaryjoin="User.id == LLMConfig.user_id",
        foreign_keys=[user_id]
    )


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    prompt_content = Column(Text, nullable=False)
    
    skill_type = Column(String(50), default="general")
    is_active = Column(Boolean, default=True)
    
    created_by = Column(Integer, index=True, nullable=True)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


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

    create_time = Column(DateTime, default=datetime.now())


class TaskExecutionLog(Base):
    __tablename__ = "task_execution_logs"

    id = Column(Integer, primary_key=True, index=True)

    periodic_task_id = Column(Integer, index=True)

    trigger_time = Column(DateTime, default=datetime.now())
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

    create_time = Column(DateTime, default=datetime.now())
    last_run_time = Column(DateTime, nullable=True)

    owner_id = Column(Integer, index=True)

    # PeriodicTask -> User (Many-to-One)
    owner = relationship(
        "User",
        primaryjoin="User.id == PeriodicTask.owner_id",
        foreign_keys=[owner_id]
    )


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=False)  # 本地存储路径
    doc_type = Column(String(50))  # pdf, docx, txt

    # 状态: pending(解析中), success(已完成), failed(失败)
    status = Column(String(20), default="pending")
    error_msg = Column(Text, nullable=True)

    chunk_count = Column(Integer, default=0)  # 切分片段数
    create_time = Column(DateTime, default=datetime.now)


class TestCaseRecord(Base):
    __tablename__ = "test_case_records"

    id = Column(Integer, primary_key=True, index=True)
    # [修改] 纯 Integer 字段，无 ForeignKey 约束，但加 index 方便查询
    user_id = Column(Integer, index=True, nullable=False)

    # 输入信息
    requirement = Column(Text, nullable=False)  # 需求描述
    image_path = Column(String(500), nullable=True)  # 图片存储路径

    # 输出结果 (存 JSON 列表)
    result_json = Column(JSON, nullable=True)

    # 状态: pending(排队), processing(生成中), success(成功), failed(失败)
    status = Column(String(50), default="pending")
    error_msg = Column(Text, nullable=True)

    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # 素材名称
    file_path = Column(String(255), nullable=False)  # 存储路径
    file_type = Column(String(50), nullable=False)  # 文件类型
    file_size = Column(Integer, nullable=False)  # 文件大小（字节）
    project_id = Column(Integer, index=True, nullable=True)  # 所属项目

    create_time = Column(DateTime, default=datetime.now())

    # Material -> Project (Many-to-One)
    project = relationship(
        "Project",
        backref=backref("materials", foreign_keys=[project_id]),
        primaryjoin="Project.id == Material.project_id",
        foreign_keys=[project_id]
    )


class NotificationConfig(Base):
    __tablename__ = "notification_configs"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)

    channel = Column(String(20), nullable=False)  # feishu, weixin, email

    is_enabled = Column(Boolean, default=True)

    config_json = Column(JSON, nullable=True)

    events = Column(JSON, nullable=True)  # ["task_success", "task_failed"]

    is_default = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.now())
    updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now())
