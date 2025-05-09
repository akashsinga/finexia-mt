# backend/app/schemas/scheduler.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, time
from enum import Enum


class TaskStatusEnum(str, Enum):
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskTypeEnum(str, Enum):
    DATA_IMPORT = "data_import"
    MODEL_TRAINING = "model_training"
    PREDICTION_GENERATION = "prediction_generation"
    PREDICTION_VERIFICATION = "prediction_verification"
    SYSTEM_MAINTENANCE = "system_maintenance"


class Schedule(BaseModel):
    enabled: bool = True
    daily: bool = True
    weekdays_only: bool = False
    time_of_day: time = Field(default=time(hour=0, minute=0))
    run_on_startup: bool = False


class ScheduledTask(BaseModel):
    id: int
    tenant_id: int
    name: str
    description: Optional[str] = None
    task_type: TaskTypeEnum
    schedule: Schedule
    parameters: Optional[Dict[str, Any]] = None
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    status: TaskStatusEnum
    created_at: datetime
    updated_at: datetime


class ScheduledTaskCreate(BaseModel):
    name: str
    description: Optional[str] = None
    task_type: TaskTypeEnum
    schedule: Schedule
    parameters: Optional[Dict[str, Any]] = None


class ScheduledTaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    schedule: Optional[Schedule] = None
    parameters: Optional[Dict[str, Any]] = None


class TaskExecutionLog(BaseModel):
    id: int
    task_id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: TaskStatusEnum
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class TasksList(BaseModel):
    tasks: List[ScheduledTask]
    count: int
