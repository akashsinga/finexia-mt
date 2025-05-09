# backend/app/websockets/auth.py
from fastapi import WebSocket, status
from jose import jwt, JWTError
import logging
from typing import Tuple, Optional, Dict, Any

from app.config import settings
from app.db.session import get_db_session

logger = logging.getLogger("finexia-api")


async def verify_token(websocket: WebSocket) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Verify JWT token from query parameters"""
    try:
        # Try to get token from query parameters
        token = websocket.query_params.get("token")

        if not token:
            logger.warning("WebSocket connection attempt without token")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return False, None

        # Verify token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        tenant_id = payload.get("tenant_id")

        if not username:
            logger.warning("Invalid token - no username")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return False, None

        # For WebSockets, tenant ID is required in token
        if not tenant_id:
            logger.warning("No tenant ID in token")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return False, None

        return True, {"username": username, "tenant_id": tenant_id, "is_admin": payload.get("is_admin", False), "user_id": payload.get("user_id")}

    except JWTError as e:
        logger.error(f"JWT validation error: {str(e)}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return False, None
    except Exception as e:
        logger.error(f"WebSocket auth error: {str(e)}")
        await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
        return False, None
