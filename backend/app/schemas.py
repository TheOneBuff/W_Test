from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum

# 基础模型
class UserBase(BaseModel):
    username: str

# 创建用户时需要密码
class UserCreate(UserBase):
    password: str

# 返回给前端时，不包含密码，包含 ID
class UserOut(UserBase):
    id: int

    class Config:
        from_attributes = True # 兼容 ORM 对象

class LLMConfigBase(BaseModel):
    provider: str
    model_name: str
    base_url: Optional[str] = None
    model_family: Optional[str] = None

class LLMConfigUpdate(LLMConfigBase):
    api_key: Optional[str] = None # 前端传来的可能是明文，也可能是掩码

class LLMConfigOut(LLMConfigBase):
    api_key_masked: Optional[str] = None # 返回给前端显示的

    class Config:
        from_attributes = True

class MenuBase(BaseModel):
    title: str
    path: Optional[str] = None
    component: Optional[str] = None
    icon: Optional[str] = None
    sort: int = 0
    parent_id: Optional[int] = None
    is_hidden: bool = False

class MenuCreate(MenuBase):
    pass

class MenuOut(MenuBase):
    id: int
    children: List['MenuOut'] = [] # 递归定义

    class Config:
        from_attributes = True


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


# --- TestCase ---
class TestCaseBase(BaseModel):
    name: str
    description: Optional[str] = None
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    script_content: str  # YAML 或 自然语言
    script_type: str = "yaml"  # yaml / prompt


class TestCaseCreate(TestCaseBase):
    pass


class TestCaseOut(TestCaseBase):
    id: int
    project_id: Optional[int] = None

    class Config:
        from_attributes = True


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectOut(ProjectBase):
    id: int
    owner_id: int
    create_time: datetime

    # owner_name 可以通过 join 查询获得，或者前端单独查

    class Config:
        from_attributes = True



class TestReportOut(BaseModel):
    id: int
    status: TaskStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    report_path: Optional[str] = None
    logs: Optional[str] = None
    # 新增
    test_case_id: int
    test_case_name: Optional[str] = None # 需要后端 join 填充

    class Config:
        from_attributes = True


class EnvBase(BaseModel):
    name: str
    description: Optional[str] = None
    project_id: Optional[int] = None
    variables: str = "{}"  # 前端传 JSON 字符串，或者用 Dict


class EnvCreate(EnvBase):
    pass


class EnvOut(EnvBase):
    id: int
    create_time: datetime

    class Config:
        from_attributes = True


class TaskLogOut(BaseModel):
    id: int
    trigger_time: datetime
    status: str
    report_ids: Optional[str]
    error_msg: Optional[str]

    class Config:
        from_attributes = True


# --- Periodic Task ---
class PeriodicTaskBase(BaseModel):
    name: str
    cron_expr: str
    target_type: str  # "project" / "cases"
    project_id: Optional[int] = None
    case_ids: Optional[str] = None
    env_id: Optional[int] = None
    is_enabled: bool = True


class PeriodicTaskCreate(PeriodicTaskBase):
    pass


class PeriodicTaskOut(PeriodicTaskBase):
    id: int
    create_time: datetime
    last_run_time: Optional[datetime] = None

    class Config:
        from_attributes = True
