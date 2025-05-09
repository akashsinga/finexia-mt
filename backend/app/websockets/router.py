# backend/app/websockets/router.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
import logging
import json
import uuid
from datetime import datetime

from app.websockets.connection_manager import connection_manager
from app.websockets.auth import verify_token
from app.api.routers.symbols import symbol_import_status

router = APIRouter()
logger = logging.getLogger("finexia-api")


@router.websocket("/ws/predictions")
async def predictions_websocket(websocket: WebSocket):
    """WebSocket endpoint for receiving prediction updates"""
    # Verify client token
    is_authenticated, user_data = await verify_token(websocket)
    if not is_authenticated:
        return

    tenant_id = user_data["tenant_id"]
    username = user_data["username"]

    # Generate a unique client ID
    client_id = f"{username}_{uuid.uuid4()}"

    # Connect to the predictions channel
    await connection_manager.connect(websocket=websocket, client_id=client_id, topic="predictions", tenant_id=tenant_id, user_id=user_data.get("user_id"))

    try:
        # Listen for client messages (could be used for filtering, etc.)
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                # Process client message if needed
                await connection_manager.send_personal_message(message={"type": "acknowledgement", "timestamp": datetime.now().isoformat(), "data": {"received": True}}, websocket=websocket)
            except json.JSONDecodeError:
                await connection_manager.send_personal_message(message={"type": "error", "timestamp": datetime.now().isoformat(), "data": {"message": "Invalid JSON format"}}, websocket=websocket)
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)


@router.websocket("/ws/pipeline")
async def pipeline_websocket(websocket: WebSocket):
    """WebSocket endpoint for pipeline status updates"""
    # Verify client token
    is_authenticated, user_data = await verify_token(websocket)
    if not is_authenticated:
        return

    tenant_id = user_data["tenant_id"]
    username = user_data["username"]

    # Generate a unique client ID
    client_id = f"{username}_{uuid.uuid4()}"

    # Connect to the pipeline channel
    await connection_manager.connect(websocket=websocket, client_id=client_id, topic="pipeline", tenant_id=tenant_id, user_id=user_data.get("user_id"))

    try:
        while True:
            await websocket.receive_text()
            # Just keep connection alive, no processing needed
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)


@router.websocket("/ws/system")
async def system_websocket(websocket: WebSocket):
    """WebSocket endpoint for system status updates"""
    # Verify client token
    is_authenticated, user_data = await verify_token(websocket)
    if not is_authenticated:
        return

    # Only admins can connect to system channel
    if not user_data.get("is_admin", False):
        await websocket.close(code=4003, reason="Admin privileges required")
        return

    tenant_id = user_data["tenant_id"]
    username = user_data["username"]

    # Generate a unique client ID
    client_id = f"{username}_{uuid.uuid4()}"

    # Connect to the system channel
    await connection_manager.connect(websocket=websocket, client_id=client_id, topic="system", tenant_id=tenant_id, user_id=user_data.get("user_id"))

    try:
        while True:
            await websocket.receive_text()
            # Just keep connection alive
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)


# Add to backend/app/websockets/router.py


@router.websocket("/ws/symbol_import/{task_id}")
async def symbol_import_websocket(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for receiving specific symbol import updates"""
    # Verify client token
    is_authenticated, user_data = await verify_token(websocket)
    if not is_authenticated:
        return

    # Only admin users can subscribe to symbol import status
    if not user_data.get("is_admin", False):
        await websocket.close(code=4003, reason="Admin privileges required")
        return

    tenant_id = user_data["tenant_id"]
    username = user_data["username"]

    # Generate a unique client ID
    client_id = f"{username}_{uuid.uuid4()}"

    # Connect to the symbol_import channel for this task
    await connection_manager.connect(websocket=websocket, client_id=client_id, topic=f"symbol_import_{task_id}", tenant_id=tenant_id, user_id=user_data.get("user_id"))

    # Send initial status if available
    if task_id in symbol_import_status:
        status_data = symbol_import_status[task_id]
        await websocket.send_json({"type": "symbol_import_status", "timestamp": datetime.now().isoformat(), "data": {"task_id": task_id, "status": status_data["status"], "started_at": status_data["started_at"], "completed_at": status_data["completed_at"], "result": status_data["result"], "error": status_data["error"]}})

    try:
        while True:
            await websocket.receive_text()
            # Keep connection alive
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
