# backend/app/websockets/message.py

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
import uuid


class MessageType(str, Enum):
    """Standard message types for WebSocket communication"""

    CONNECTION = "connection"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    NOTIFICATION = "notification"
    DATA = "data"
    STATUS_UPDATE = "status_update"
    PROGRESS = "progress"
    COMMAND = "command"


class WebSocketMessage(BaseModel):
    """Standard format for WebSocket messages"""

    type: MessageType
    timestamp: datetime = Field(default_factory=datetime.now)
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: Optional[int] = None
    topic: str
    data: Dict[str, Any]


def create_message(message_type: MessageType, topic: str, data: Dict[str, Any], tenant_id: Optional[int] = None) -> Dict[str, Any]:
    """Create a standardized WebSocket message"""
    msg = WebSocketMessage(
        type=message_type,
        # Use string rather than datetime object directly
        timestamp=datetime.now().isoformat(),
        topic=topic,
        data=data,
        tenant_id=tenant_id,
    )
    return msg.dict()
