# backend/app/schemas/websocket.py
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime


class WebSocketMessageType(str, Enum):
    PREDICTION = "prediction"
    PIPELINE_STATUS = "pipeline_status"
    MODEL_STATUS = "model_status"
    SYSTEM_STATUS = "system_status"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


class WebSocketMessage(BaseModel):
    type: WebSocketMessageType
    timestamp: datetime = datetime.now()
    data: Dict[str, Any]
    tenant_id: Optional[int] = None


class ConnectionStats(BaseModel):
    active_connections: int
    clients_by_tenant: Dict[str, int]
    topics: List[str]
