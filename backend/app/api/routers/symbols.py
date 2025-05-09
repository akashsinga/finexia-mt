# backend/app/api/routers/symbols.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import asyncio

from app.db.session import get_db_session
from app.schemas.symbol import SymbolResponse
from app.services.symbol_service import get_symbols_for_tenant, get_symbol_for_tenant, get_all_symbols
from app.api.deps import get_current_tenant, get_current_user, get_current_superadmin
from app.scripts.import_symbol_master import import_symbols as import_symbols_task
from app.websockets.connection_manager import connection_manager

router = APIRouter()

# In-memory tracking of import status
symbol_import_status = {}


@router.get("", response_model=List[SymbolResponse])
async def list_symbols(active_only: bool = Query(True, description="Only show active symbols"), fo_eligible: Optional[bool] = Query(None, description="Filter by F&O eligibility"), skip: int = Query(0, description="Number of records to skip"), limit: int = Query(100, description="Maximum number of records to return"), db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_user)):
    """List symbols for current tenant"""
    return get_symbols_for_tenant(db, tenant.id, active_only, fo_eligible, skip, limit)


@router.get("/all", response_model=List[SymbolResponse])
async def list_all_symbols(active_only: bool = Query(True, description="Only show active symbols"), db: Session = Depends(get_db_session), current_user=Depends(get_current_superadmin)):  # Only superadmins
    """List all symbols across tenants (superadmin only)"""
    return get_all_symbols(db, active_only)


@router.get("/{symbol_id}", response_model=SymbolResponse)
async def get_symbol_by_id(symbol_id: int = Path(..., description="Symbol ID"), db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_user)):
    """Get symbol by ID for current tenant"""
    symbol = get_symbol_for_tenant(db, symbol_id, tenant.id)
    if not symbol:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Symbol not found")
    return symbol


async def notify_symbol_import_status(task_id: str, status: str, details: Dict[str, Any] = None):
    """Send WebSocket notification about symbol import status"""
    message = {"type": "symbol_import_status", "timestamp": datetime.now().isoformat(), "data": {"task_id": task_id, "status": status, **(details or {})}}

    # Broadcast to all clients in the system topic
    await connection_manager.broadcast(message, "system")

    # Also broadcast to symbol_import topic for specific subscribers
    await connection_manager.broadcast(message, f"symbol_import_{task_id}")


async def run_symbol_import_task(task_id: str, force_download: bool):
    """Background task for symbol import that updates status tracking and sends WebSocket notifications"""
    try:
        # Update status to started
        status_data = {"status": "started", "started_at": datetime.now().isoformat(), "completed_at": None, "result": None, "error": None}
        symbol_import_status[task_id] = status_data

        # Send initial notification
        await notify_symbol_import_status(task_id, "started", {"started_at": status_data["started_at"], "message": "Symbol import started"})

        # Send progress update - downloading
        await notify_symbol_import_status(task_id, "downloading", {"message": "Downloading symbol data"})

        # Run import task
        result = import_symbols_task(force_download)

        # Update status with result
        status = "completed" if result["success"] else "failed"
        symbol_import_status[task_id]["status"] = status
        symbol_import_status[task_id]["completed_at"] = datetime.now().isoformat()
        symbol_import_status[task_id]["result"] = result.get("stats")
        symbol_import_status[task_id]["error"] = result.get("error")

        # Send final notification
        await notify_symbol_import_status(task_id, status, {"completed_at": symbol_import_status[task_id]["completed_at"], "result": result.get("stats"), "error": result.get("error"), "message": "Symbol import completed successfully" if result["success"] else f"Symbol import failed: {result.get('error')}"})

    except Exception as e:
        # Update status with error
        error_msg = str(e)
        symbol_import_status[task_id]["status"] = "failed"
        symbol_import_status[task_id]["completed_at"] = datetime.now().isoformat()
        symbol_import_status[task_id]["error"] = error_msg

        # Send error notification
        await notify_symbol_import_status(task_id, "failed", {"completed_at": symbol_import_status[task_id]["completed_at"], "error": error_msg, "message": f"Symbol import failed: {error_msg}"})


@router.post("/import", response_model=Dict[str, Any])
async def import_symbols(background_tasks: BackgroundTasks, force_download: bool = Query(False, description="Force download instead of using cache"), db: Session = Depends(get_db_session), current_user=Depends(get_current_superadmin)):  # Only superadmins can import symbols
    """
    Import symbols from external source (superadmin only)

    This endpoint triggers the import of symbols from the configured data source.
    It can be used to update the global symbol repository used across all tenants.
    The import runs as a background task and progress is reported via WebSocket.

    To receive real-time updates:
    1. Connect to WebSocket endpoint /ws/system
    2. Or connect to task-specific endpoint /ws/symbol_import/{task_id}
    """
    # Generate task ID for tracking
    task_id = str(uuid.uuid4())

    # Start background task
    background_tasks.add_task(run_symbol_import_task, task_id, force_download)

    return {"message": "Symbol import started in background", "status": "started", "task_id": task_id, "started_at": datetime.now().isoformat(), "websocket_topic": f"symbol_import_{task_id}"}


@router.get("/import/status/{task_id}", response_model=Dict[str, Any])
async def get_import_status(task_id: str = Path(..., description="Import task ID"), current_user=Depends(get_current_superadmin)):  # Only superadmins can check import status
    """
    Get the status of a symbol import task

    Returns the current status of a previously initiated symbol import task.
    """
    if task_id not in symbol_import_status:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import task not found")

    return symbol_import_status[task_id]
