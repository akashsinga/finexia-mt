# backend/app/schemas/system.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class SystemStatusResponse(BaseModel):
    status: str
    server_time: datetime
    database_status: str
    total_predictions: int
    today_predictions: int
    verified_predictions: int
    verification_rate: float
    tenant_id: int
    tenant_name: str
    symbols_count: int


class PipelineRunRequest(BaseModel):
    force: bool = False
    steps: Optional[List[str]] = None


class PipelineRunResponse(BaseModel):
    message: str
    started_at: datetime
    requested_by: str
    status: str
