# backend/app/websockets/auth.py
from fastapi import WebSocket, status
from jose import jwt, JWTError
import logging
from typing import Tuple, Optional, Dict, Any
import time
from datetime import datetime

from app.config import settings
from app.db.session import get_db_session

logger = logging.getLogger("finexia-api")

# Track connection attempts by IP
connection_attempts = {}
# Max 10 connection attempts per minute per IP
MAX_CONN_ATTEMPTS = 10
ATTEMPT_WINDOW = 60  # seconds


async def check_rate_limit(websocket: WebSocket) -> bool:
    """Check if client is rate limited"""
    client_ip = websocket.client.host
    current_time = time.time()

    # Initialize or clean up old attempts
    if client_ip not in connection_attempts:
        connection_attempts[client_ip] = []
    else:
        # Remove attempts older than the window
        connection_attempts[client_ip] = [t for t in connection_attempts[client_ip] if current_time - t < ATTEMPT_WINDOW]

    # Check if too many attempts
    if len(connection_attempts[client_ip]) >= MAX_CONN_ATTEMPTS:
        logger.warning(f"Rate limit exceeded for {client_ip}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return False

    # Record this attempt
    connection_attempts[client_ip].append(current_time)
    return True


async def verify_token(websocket: WebSocket) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Verify JWT token from query parameters with rate limiting"""
    # Check rate limit first
    if not await check_rate_limit(websocket):
        return False, None

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

        # Add expiration check
        if "exp" in payload:
            expiration = datetime.fromtimestamp(payload["exp"])
            if datetime.utcnow() > expiration:
                logger.warning(f"Expired token from {username}")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token expired")
                return False, None

        if not username:
            logger.warning("Invalid token - no username")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return False, None

        # For WebSockets, tenant ID is required in token
        if not tenant_id:
            logger.warning("No tenant ID in token")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return False, None

        return True, {"username": username, "tenant_id": tenant_id, "is_admin": payload.get("is_admin", False), "is_superadmin": payload.get("is_superadmin", False), "user_id": payload.get("user_id")}

    except JWTError as e:
        logger.error(f"JWT validation error: {str(e)}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return False, None
    except Exception as e:
        logger.error(f"WebSocket auth error: {str(e)}")
        await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
        return False, None
