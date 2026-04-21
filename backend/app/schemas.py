from pydantic import BaseModel
from typing import List, Optional, Any
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
    name: str
    provider: str
    model_name: str
    base_url: Optional[str] = None
    model_family: Optional[str] = None
    memo: Optional[str] = None
    model_type: Optional[str] = "text"

    # [修改] 这里不再需要 is_active 和 use_for，因为前端单独控制
    # 如果前端表单提交时不需要设置激活状态，这里可以不写，
    # 或者写上 Optional[bool] 作为默认值


class LLMConfigCreate(LLMConfigBase):
    api_key: Optional[str] = None


class LLMConfigUpdate(LLMConfigCreate):
    pass


class LLMConfig(LLMConfigBase):
    id: int
    api_key_masked: Optional[str] = None
    is_active_chat: bool = False
    is_active_gen: bool = False
    is_active_exec: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- [新增] 测试用例记录 ---
class TestCaseRecord(BaseModel):
    id: int
    requirement: str
    image_path: Optional[str]
    status: str
    result_json: Optional[List[Any]]
    create_time: datetime
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
    script_type: str = "yaml"  # yaml / prompt / typescript
    case_type: str = "web"  # web / pc


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


class MaterialBase(BaseModel):
    name: str
    project_id: Optional[int] = None
    category: str = "web"  # 素材分类: web/pc


class MaterialCreate(MaterialBase):
    pass


class MaterialOut(MaterialBase):
    id: int
    file_path: str
    file_type: str
    file_size: int
    category: str
    create_time: datetime

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


class NotificationConfigBase(BaseModel):
    name: str
    channel: str
    is_enabled: bool = True
    config_json: Optional[dict] = None
    events: Optional[list] = None
    is_default: bool = False


class NotificationConfigCreate(NotificationConfigBase):
    pass


class NotificationConfigUpdate(NotificationConfigBase):
    pass


class NotificationConfigOut(NotificationConfigBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationTestRequest(BaseModel):
    config_id: int
    test_message: Optional[str] = "这是一条测试通知"


class NotificationTestResponse(BaseModel):
    success: bool
    message: str


class SkillCreate(BaseModel):
    name: str
    description: Optional[str] = None
    prompt_content: str
    skill_type: str = "general"
    is_active: bool = True


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    prompt_content: Optional[str] = None
    skill_type: Optional[str] = None
    is_active: Optional[bool] = None


class SkillOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    prompt_content: str
    skill_type: str
    is_active: bool
    created_by: Optional[int] = None
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True


class ExecutorRegister(BaseModel):
    name: str
    uuid: str
    executor_type: str = "pc"
    version: Optional[str] = None
    ip_address: Optional[str] = None
    os_version: Optional[str] = None
    hostname: Optional[str] = None
    capabilities: Optional[dict] = None


class ExecutorCreate(ExecutorRegister):
    pass


class ExecutorUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class ExecutorOut(BaseModel):
    id: int
    uuid: str
    name: str
    executor_type: str
    version: Optional[str] = None
    ip_address: Optional[str] = None
    os_version: Optional[str] = None
    hostname: Optional[str] = None
    status: str
    last_heartbeat: Optional[datetime] = None
    capabilities: Optional[dict] = None
    is_active: bool
    create_time: datetime

    class Config:
        from_attributes = True