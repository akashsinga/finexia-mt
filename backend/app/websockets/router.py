# backend/app/websockets/router.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
import logging
import json
import uuid
import asyncio
from datetime import datetime
from fastapi.encoders import jsonable_encoder

from app.websockets.connection_manager import connection_manager
from app.websockets.auth import verify_token
from app.api.routers.symbols import symbol_import_status
from app.services.feature_data_service import get_feature_calculation_status
from app.services.prediction_service import prediction_task_status
from app.websockets.message import create_message, MessageType

router = APIRouter()
logger = logging.getLogger("finexia-api")


# Helper method to safely send JSON with datetime objects
async def safe_send_json(websocket: WebSocket, message: dict):
    """Send JSON data with proper handling of datetime objects"""
    try:
        # Convert message to JSON-compatible format
        json_compatible_message = jsonable_encoder(message)
        await websocket.send_json(json_compatible_message)
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        # Try a fallback approach - convert datetimes to strings manually
        try:
            if "timestamp" in message and isinstance(message["timestamp"], datetime):
                message["timestamp"] = message["timestamp"].isoformat()

            # Handle nested datetimes in data
            if "data" in message and isinstance(message["data"], dict):
                for key, value in message["data"].items():
                    if isinstance(value, datetime):
                        message["data"][key] = value.isoformat()

            await websocket.send_json(message)
        except Exception as nested_e:
            logger.error(f"Failed to send message even with fallback: {str(nested_e)}")
            raise


@router.websocket("/ws/predictions")
async def predictions_websocket(websocket: WebSocket):
    """WebSocket endpoint for receiving prediction updates with improved error handling"""
    try:
        # Verify client token with rate limiting
        is_authenticated, user_data = await verify_token(websocket)
        if not is_authenticated:
            return

        tenant_id = user_data["tenant_id"]
        username = user_data["username"]

        # Generate a unique client ID
        client_id = f"{username}_{uuid.uuid4()}"

        # Connect to the predictions channel
        await connection_manager.connect(websocket=websocket, client_id=client_id, topic="predictions", tenant_id=tenant_id, user_id=user_data.get("user_id"))

        # Start heartbeat monitor if not already running
        await connection_manager.start_heartbeat_monitor()

        # Welcome message using standardized format
        welcome_msg = create_message(MessageType.CONNECTION, "predictions", {"message": "Connected to predictions channel"}, tenant_id)
        await safe_send_json(websocket, welcome_msg)

        # Main message loop with timeout handling
        while True:
            try:
                # Wait for message with timeout
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)  # 1 minute timeout

                # Record heartbeat
                await connection_manager.record_heartbeat(websocket)

                # Increment received message count
                connection_manager.connection_stats["total_messages_received"] += 1

                # Process message if it's not a heartbeat
                if data and data != "heartbeat":
                    try:
                        message = json.loads(data)
                        # Process message...
                        response = create_message(MessageType.DATA, "predictions", {"received": True}, tenant_id)
                        await safe_send_json(websocket, response)
                    except json.JSONDecodeError:
                        error_msg = create_message(MessageType.ERROR, "predictions", {"message": "Invalid JSON format"}, tenant_id)
                        await safe_send_json(websocket, error_msg)
            except asyncio.TimeoutError:
                # Connection idle too long, send ping to check
                try:
                    ping_msg = create_message(MessageType.HEARTBEAT, "predictions", {"ping": True}, tenant_id)
                    await safe_send_json(websocket, ping_msg)
                except:
                    # Failed to send ping, connection likely dead
                    break

    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Error in predictions websocket: {str(e)}")
        try:
            await websocket.close(code=1011)
        except:
            pass


@router.websocket("/ws/pipeline")
async def pipeline_websocket(websocket: WebSocket):
    """WebSocket endpoint for pipeline status updates"""
    try:
        # Verify client token with rate limiting
        is_authenticated, user_data = await verify_token(websocket)
        if not is_authenticated:
            return

        tenant_id = user_data["tenant_id"]
        username = user_data["username"]

        # Generate a unique client ID
        client_id = f"{username}_{uuid.uuid4()}"

        # Connect to the pipeline channel
        await connection_manager.connect(websocket=websocket, client_id=client_id, topic="pipeline", tenant_id=tenant_id, user_id=user_data.get("user_id"))

        # Start heartbeat monitor
        await connection_manager.start_heartbeat_monitor()

        # Welcome message
        welcome_msg = create_message(MessageType.CONNECTION, "pipeline", {"message": "Connected to pipeline channel"}, tenant_id)
        await safe_send_json(websocket, welcome_msg)

        # Main message loop
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)

                # Record heartbeat
                await connection_manager.record_heartbeat(websocket)

                # Increment received message count
                connection_manager.connection_stats["total_messages_received"] += 1

            except asyncio.TimeoutError:
                # Send ping
                try:
                    ping_msg = create_message(MessageType.HEARTBEAT, "pipeline", {"ping": True}, tenant_id)
                    await safe_send_json(websocket, ping_msg)
                except:
                    break
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Error in pipeline websocket: {str(e)}")
        try:
            await websocket.close(code=1011)
        except:
            pass


@router.websocket("/ws/system")
async def system_websocket(websocket: WebSocket):
    """WebSocket endpoint for system status updates"""
    try:
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

        # Start heartbeat monitor
        await connection_manager.start_heartbeat_monitor()

        # Welcome message
        welcome_msg = create_message(MessageType.CONNECTION, "system", {"message": "Connected to system channel"}, tenant_id)
        await safe_send_json(websocket, welcome_msg)

        # Main message loop
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)

                # Record heartbeat
                await connection_manager.record_heartbeat(websocket)

                # Increment received message count
                connection_manager.connection_stats["total_messages_received"] += 1

            except asyncio.TimeoutError:
                # Send ping
                try:
                    ping_msg = create_message(MessageType.HEARTBEAT, "system", {"ping": True}, tenant_id)
                    await safe_send_json(websocket, ping_msg)
                except:
                    break
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Error in system websocket: {str(e)}")
        try:
            await websocket.close(code=1011)
        except:
            pass


@router.websocket("/ws/symbol_import/{task_id}")
async def symbol_import_websocket(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for receiving specific symbol import updates"""
    try:
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

        # Start heartbeat monitor
        await connection_manager.start_heartbeat_monitor()

        # Send initial status if available
        if task_id in symbol_import_status:
            status_data = symbol_import_status[task_id]
            status_msg = create_message(MessageType.STATUS_UPDATE, f"symbol_import_{task_id}", {"task_id": task_id, "status": status_data["status"], "started_at": status_data["started_at"], "completed_at": status_data["completed_at"], "result": status_data["result"], "error": status_data["error"]}, tenant_id)
            await safe_send_json(websocket, status_msg)

        # Main message loop
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)

                # Record heartbeat
                await connection_manager.record_heartbeat(websocket)

                # Increment received message count
                connection_manager.connection_stats["total_messages_received"] += 1

            except asyncio.TimeoutError:
                # Send ping
                try:
                    ping_msg = create_message(MessageType.HEARTBEAT, f"symbol_import_{task_id}", {"ping": True}, tenant_id)
                    await safe_send_json(websocket, ping_msg)
                except:
                    break
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Error in symbol import websocket: {str(e)}")
        try:
            await websocket.close(code=1011)
        except:
            pass


@router.websocket("/ws/eod_import/{task_id}")
async def eod_import_websocket(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for receiving updates about EOD data import"""
    try:
        # Verify client token
        is_authenticated, user_data = await verify_token(websocket)
        if not is_authenticated:
            return

        # Only superadmins can subscribe to import status
        if not user_data.get("is_superadmin", False):
            await websocket.close(code=4003, reason="Superadmin privileges required")
            return

        # Generate a unique client ID
        username = user_data.get("username", "unknown")
        client_id = f"{username}_{uuid.uuid4()}"
        tenant_id = user_data.get("tenant_id")

        # Connect to the specific channel for this import task
        await connection_manager.connect(websocket, client_id, f"eod_import_{task_id}", tenant_id=tenant_id)

        # Start heartbeat monitor
        await connection_manager.start_heartbeat_monitor()

        # Send initial status if available
        from app.services.eod_data_service import get_import_status

        status = get_import_status(task_id)
        if status.get("status") != "not_found":
            status_msg = create_message(MessageType.STATUS_UPDATE, f"eod_import_{task_id}", status, tenant_id)
            await safe_send_json(websocket, status_msg)

        # Main message loop
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)

                # Record heartbeat
                await connection_manager.record_heartbeat(websocket)

                # Increment received message count
                connection_manager.connection_stats["total_messages_received"] += 1

            except asyncio.TimeoutError:
                # Send ping
                try:
                    ping_msg = create_message(MessageType.HEARTBEAT, f"eod_import_{task_id}", {"ping": True}, tenant_id)
                    await safe_send_json(websocket, ping_msg)
                except:
                    break
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Error in EOD import websocket: {str(e)}")
        try:
            await websocket.close(code=1011)
        except:
            pass


@router.websocket("/ws/model_training/{task_id}")
async def model_training_websocket(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for receiving model training updates"""
    try:
        # Verify client token
        is_authenticated, user_data = await verify_token(websocket)
        if not is_authenticated:
            return

        # Only admin users can subscribe to model training status
        if not user_data.get("is_admin", False):
            await websocket.close(code=4003, reason="Admin privileges required")
            return

        tenant_id = user_data["tenant_id"]
        username = user_data["username"]

        # Generate a unique client ID
        client_id = f"{username}_{uuid.uuid4()}"

        # Connect to the model_training channel for this task
        await connection_manager.connect(websocket=websocket, client_id=client_id, topic=f"model_training_{task_id}", tenant_id=tenant_id, user_id=user_data.get("user_id"))

        # Start heartbeat monitor
        await connection_manager.start_heartbeat_monitor()

        # Welcome message
        welcome_msg = create_message(MessageType.CONNECTION, f"model_training_{task_id}", {"message": f"Connected to model training channel for task {task_id}"}, tenant_id)
        await safe_send_json(websocket, welcome_msg)

        # Check if there's existing status data for this task
        from app.core.train.daily_trainer import model_training_status

        if hasattr(model_training_status, task_id) and task_id in model_training_status:
            status_data = model_training_status[task_id]
            status_msg = create_message(MessageType.STATUS_UPDATE, f"model_training_{task_id}", status_data, tenant_id)
            await safe_send_json(websocket, status_msg)

        # Main message loop
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)

                # Record heartbeat
                await connection_manager.record_heartbeat(websocket)

                # Increment received message count
                connection_manager.connection_stats["total_messages_received"] += 1

            except asyncio.TimeoutError:
                # Send ping
                try:
                    ping_msg = create_message(MessageType.HEARTBEAT, f"model_training_{task_id}", {"ping": True}, tenant_id)
                    await safe_send_json(websocket, ping_msg)
                except:
                    break
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Error in model training websocket: {str(e)}")
        try:
            await websocket.close(code=1011)
        except:
            pass


@router.websocket("/ws/feature_calculation/{calculation_id}")
async def feature_calculation_websocket(websocket: WebSocket, calculation_id: str):
    """WebSocket endpoint for receiving feature calculation updates"""
    try:
        # Verify client token
        is_authenticated, user_data = await verify_token(websocket)
        if not is_authenticated:
            return

        # Only admin users can subscribe
        if not user_data.get("is_admin", False):
            await websocket.close(code=4003, reason="Admin privileges required")
            return

        tenant_id = user_data["tenant_id"]
        username = user_data["username"]

        # Generate a unique client ID
        client_id = f"{username}_{uuid.uuid4()}"

        # Connect to the feature_calculation channel for this task
        await connection_manager.connect(websocket=websocket, client_id=client_id, topic=f"feature_calculation_{calculation_id}", tenant_id=tenant_id, user_id=user_data.get("user_id"))

        # Start heartbeat monitor
        await connection_manager.start_heartbeat_monitor()

        # Send initial status if available
        status = get_feature_calculation_status(calculation_id)
        if status.get("status") != "not_found":
            status_msg = create_message(MessageType.STATUS_UPDATE, f"feature_calculation_{calculation_id}", status, tenant_id)
            await safe_send_json(websocket, status_msg)

        # Main message loop
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)

                # Record heartbeat
                await connection_manager.record_heartbeat(websocket)

                # Increment received message count
                connection_manager.connection_stats["total_messages_received"] += 1

            except asyncio.TimeoutError:
                # Send ping
                try:
                    ping_msg = create_message(MessageType.HEARTBEAT, f"feature_calculation_{calculation_id}", {"ping": True}, tenant_id)
                    await safe_send_json(websocket, ping_msg)
                except:
                    break
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Error in feature calculation websocket: {str(e)}")
        try:
            await websocket.close(code=1011)
        except:
            pass


@router.websocket("/ws/predictions/{task_id}")
async def predictions_task_websocket(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for receiving status updates on a prediction task"""
    try:
        # Verify client token
        is_authenticated, user_data = await verify_token(websocket)
        if not is_authenticated:
            return

        tenant_id = user_data["tenant_id"]
        username = user_data["username"]

        # Generate a unique client ID
        client_id = f"{username}_{uuid.uuid4()}"

        # Connect to the predictions channel for this task
        topic = f"predictions_{task_id}"
        await connection_manager.connect(websocket=websocket, client_id=client_id, topic=topic, tenant_id=tenant_id, user_id=user_data.get("user_id"))

        # Start heartbeat monitor
        await connection_manager.start_heartbeat_monitor()

        # Send initial status if available
        if task_id in prediction_task_status:
            status_data = prediction_task_status[task_id]
            status_msg = create_message(MessageType.STATUS_UPDATE, topic, {"task_id": task_id, "status": status_data}, tenant_id)
            await safe_send_json(websocket, status_msg)

        # Main message loop
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)

                # Record heartbeat
                await connection_manager.record_heartbeat(websocket)

                # Increment received message count
                connection_manager.connection_stats["total_messages_received"] += 1

            except asyncio.TimeoutError:
                # Send ping
                try:
                    ping_msg = create_message(MessageType.HEARTBEAT, topic, {"ping": True}, tenant_id)
                    await safe_send_json(websocket, ping_msg)
                except:
                    break
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Error in predictions task websocket: {str(e)}")
        try:
            await websocket.close(code=1011)
        except:
            pass


@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates"""
    try:
        # Verify client token
        is_authenticated, user_data = await verify_token(websocket)
        if not is_authenticated:
            return

        tenant_id = user_data["tenant_id"]
        username = user_data["username"]

        # Generate a unique client ID
        client_id = f"{username}_{uuid.uuid4()}"

        # Connect to the dashboard channel
        await connection_manager.connect(websocket=websocket, client_id=client_id, topic="dashboard", tenant_id=tenant_id, user_id=user_data.get("user_id"))

        # Start heartbeat monitor
        await connection_manager.start_heartbeat_monitor()

        # Welcome message
        welcome_msg = create_message(MessageType.CONNECTION, "dashboard", {"message": "Connected to dashboard channel"}, tenant_id)
        await safe_send_json(websocket, welcome_msg)

        # Main message loop
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)

                # Record heartbeat
                await connection_manager.record_heartbeat(websocket)

                # Increment received message count
                connection_manager.connection_stats["total_messages_received"] += 1

            except asyncio.TimeoutError:
                # Send ping
                try:
                    ping_msg = create_message(MessageType.HEARTBEAT, "dashboard", {"ping": True}, tenant_id)
                    await safe_send_json(websocket, ping_msg)
                except:
                    break
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Error in dashboard websocket: {str(e)}")
        try:
            await websocket.close(code=1011)
        except:
            pass


@router.websocket("/ws/error_test")
async def error_handling_test(websocket: WebSocket):
    """Endpoint to test error handling"""
    try:
        # Accept the connection
        await websocket.accept()

        # Send a test message with datetime to verify serialization
        test_message = {"type": "test", "timestamp": datetime.now(), "data": {"message": "This is a test message with datetime", "current_time": datetime.now()}}

        # Use the safe send method
        await safe_send_json(websocket, test_message)

        # Set a timeout for operations
        await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
    except asyncio.TimeoutError:
        # Handle timeout
        await safe_send_json(websocket, {"type": "error", "timestamp": datetime.now().isoformat(), "data": {"message": "Connection timed out"}})
        await websocket.close(code=1001, reason="Connection timeout")
    except WebSocketDisconnect as e:
        # Handle client disconnect
        logger.info(f"Client disconnected with code {e.code}")
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"WebSocket error: {str(e)}")
        try:
            await safe_send_json(websocket, {"type": "error", "timestamp": datetime.now().isoformat(), "data": {"message": "Internal server error"}})
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass  # Connection might already be closed
