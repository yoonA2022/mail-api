"""
定时任务模型
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class TaskType(str, Enum):
    """任务类型枚举"""
    EMAIL_SYNC = "email_sync"
    ORDER_SYNC = "order_sync"
    CLEANUP = "cleanup"
    BACKUP = "backup"
    CUSTOM = "custom"


class TaskStatus(str, Enum):
    """任务状态枚举"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    RUNNING = "running"
    ERROR = "error"


class ExecutionStatus(str, Enum):
    """执行状态枚举"""
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class CronTaskBase(BaseModel):
    """定时任务基础模型"""
    name: str = Field(..., description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    type: TaskType = Field(TaskType.CUSTOM, description="任务类型")
    cron_expression: str = Field(..., description="Cron表达式")
    timezone: str = Field("Asia/Shanghai", description="时区")
    command: str = Field(..., description="执行命令")
    parameters: Optional[Dict[str, Any]] = Field(None, description="执行参数")
    working_directory: Optional[str] = Field(None, description="工作目录")
    environment_vars: Optional[Dict[str, str]] = Field(None, description="环境变量")
    timeout_seconds: int = Field(300, description="超时时间（秒）")
    max_retries: int = Field(3, description="最大重试次数")
    retry_interval: int = Field(60, description="重试间隔（秒）")
    notify_on_success: bool = Field(False, description="成功时是否通知")
    notify_on_failure: bool = Field(True, description="失败时是否通知")
    notification_emails: Optional[List[str]] = Field(None, description="通知邮箱列表")
    priority: int = Field(5, description="优先级（1-10）")
    tags: Optional[List[str]] = Field(None, description="标签")
    remark: Optional[str] = Field(None, description="备注说明")


class CronTaskCreate(CronTaskBase):
    """创建定时任务模型"""
    is_active: bool = Field(True, description="是否激活")


class CronTaskUpdate(BaseModel):
    """更新定时任务模型"""
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[TaskType] = None
    cron_expression: Optional[str] = None
    timezone: Optional[str] = None
    command: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    working_directory: Optional[str] = None
    environment_vars: Optional[Dict[str, str]] = None
    status: Optional[TaskStatus] = None
    is_active: Optional[bool] = None
    timeout_seconds: Optional[int] = None
    max_retries: Optional[int] = None
    retry_interval: Optional[int] = None
    notify_on_success: Optional[bool] = None
    notify_on_failure: Optional[bool] = None
    notification_emails: Optional[List[str]] = None
    priority: Optional[int] = None
    tags: Optional[List[str]] = None
    remark: Optional[str] = None


class CronTask(CronTaskBase):
    """定时任务完整模型"""
    id: int
    status: TaskStatus = TaskStatus.ENABLED
    is_active: bool = True
    run_count: int = 0
    success_count: int = 0
    error_count: int = 0
    last_run_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_error_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CronTaskLog(BaseModel):
    """定时任务执行日志模型"""
    id: int
    task_id: int
    task_name: str
    execution_id: str
    status: ExecutionStatus
    trigger_type: str = "scheduled"
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    exit_code: Optional[int] = None
    output: Optional[str] = None
    error_output: Optional[str] = None
    error_message: Optional[str] = None
    server_hostname: Optional[str] = None
    server_ip: Optional[str] = None
    process_id: Optional[int] = None
    retry_count: int = 0
    max_retries: Optional[int] = None
    is_retry: bool = False
    parent_log_id: Optional[int] = None
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    triggered_by: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CronTaskOverview(BaseModel):
    """定时任务概览模型"""
    id: int
    name: str
    description: Optional[str]
    type: TaskType
    cron_expression: str
    status: TaskStatus
    is_active: bool
    run_count: int
    success_count: int
    error_count: int
    success_rate_percent: float
    last_run_at: Optional[datetime]
    last_success_at: Optional[datetime]
    last_error_at: Optional[datetime]
    next_run_at: Optional[datetime]
    priority: int
    created_at: datetime
    created_by_username: Optional[str]
    last_execution_status: Optional[ExecutionStatus]
    last_execution_duration_ms: Optional[int]

    class Config:
        from_attributes = True


class CronTaskListResponse(BaseModel):
    """定时任务列表响应模型"""
    tasks: List[CronTaskOverview]
    total: int
    page: int
    page_size: int
    total_pages: int


class CronTaskStatsResponse(BaseModel):
    """定时任务统计响应模型"""
    total_tasks: int
    enabled_tasks: int
    disabled_tasks: int
    running_tasks: int
    error_tasks: int
    total_executions: int
    success_executions: int
    error_executions: int
    success_rate: float
