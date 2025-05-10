# app/api/routers/symbols.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Path, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from app.db.session import get_db_session
from app.schemas.symbol import SymbolResponse, SymbolList, SymbolStatsResponse
from app.api.deps import get_current_tenant, get_current_user, get_current_active_admin, get_current_superadmin
from app.services.symbol_service import get_symbols, get_symbol_by_id, search_symbols, get_symbols_with_stats
from app.scripts.import_symbol_master import import_symbols

router = APIRouter()

# In-memory tracking of import status
symbol_import_status = {}


# Symbol Access (All Users)
@router.get("", response_model=SymbolList)
async def list_symbols(active_only: bool = Query(True, description="Only show active symbols"), fo_eligible: Optional[bool] = Query(None, description="Filter by F&O eligibility"), skip: int = Query(0, description="Number of records to skip"), limit: int = Query(100, description="Maximum number of records to return"), db: Session = Depends(get_db_session), current_user=Depends(get_current_user)):
    """List all symbols with filtering options"""
    symbols = get_symbols(db, active_only, fo_eligible, skip, limit)
    return SymbolList(symbols=symbols, count=len(symbols))


@router.get("/{symbol_id}", response_model=SymbolResponse)
async def get_symbol_details(symbol_id: int = Path(..., description="Symbol ID"), db: Session = Depends(get_db_session), current_user=Depends(get_current_user)):
    """Get symbol by ID"""
    symbol = get_symbol_by_id(db, symbol_id)
    if not symbol:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Symbol not found")
    return symbol


@router.get("/search", response_model=SymbolList)
async def search_symbols_endpoint(query: str = Query(..., description="Search term", min_length=2), active_only: bool = Query(True, description="Only show active symbols"), db: Session = Depends(get_db_session), current_user=Depends(get_current_user)):
    """Search symbols by name or code"""
    symbols = search_symbols(db, query, active_only)
    return SymbolList(symbols=symbols, count=len(symbols))


# Admin-only Symbol Operations
@router.get("/admin/all", response_model=SymbolList)
async def admin_list_symbols(active_only: bool = Query(False, description="Filter by active status"), db: Session = Depends(get_db_session), current_superadmin=Depends(get_current_superadmin)):
    """Admin view of all symbols (superadmin only)"""
    symbols = get_symbols(db, active_only)
    return SymbolList(symbols=symbols, count=len(symbols))


@router.post("/admin/import", response_model=Dict[str, Any])
async def import_symbols_endpoint(background_tasks: BackgroundTasks, force_download: bool = Query(False, description="Force download instead of using cache"), db: Session = Depends(get_db_session), current_superadmin=Depends(get_current_superadmin)):
    """Import symbols from external source (superadmin only)"""
    # Generate task ID for tracking
    task_id = str(uuid.uuid4())

    # Initialize status tracking
    symbol_import_status[task_id] = {"status": "created", "started_at": datetime.now().isoformat(), "completed_at": None, "result": None, "error": None}

    # Run import in background
    background_tasks.add_task(run_symbol_import, task_id, force_download)

    return {"message": "Symbol import started in background", "status": "started", "task_id": task_id, "started_at": datetime.now().isoformat(), "websocket_topic": f"symbol_import_{task_id}"}


@router.get("/admin/import/status/{task_id}", response_model=Dict[str, Any])
async def get_import_status(task_id: str = Path(..., description="Import task ID"), current_superadmin=Depends(get_current_superadmin)):
    """Get the status of a symbol import task (superadmin only)"""
    if task_id not in symbol_import_status:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import task not found")

    return symbol_import_status[task_id]


@router.get("/admin/stats", response_model=SymbolStatsResponse)
async def get_symbol_statistics(db: Session = Depends(get_db_session), current_superadmin=Depends(get_current_superadmin)):
    """Get system-wide symbol statistics (superadmin only)"""
    stats = get_symbols_with_stats(db)
    return stats


# Helper function for background task
async def run_symbol_import(task_id: str, force_download: bool):
    """Background task for symbol import"""
    try:
        # Update status to started
        symbol_import_status[task_id]["status"] = "started"

        # Run the import
        result = import_symbols(force_download)

        # Update status with result
        symbol_import_status[task_id]["status"] = "completed" if result["success"] else "failed"
        symbol_import_status[task_id]["completed_at"] = datetime.now().isoformat()
        symbol_import_status[task_id]["result"] = result.get("stats")
        symbol_import_status[task_id]["error"] = result.get("error")

    except Exception as e:
        # Update status with error
        symbol_import_status[task_id]["status"] = "failed"
        symbol_import_status[task_id]["completed_at"] = datetime.now().isoformat()
        symbol_import_status[task_id]["error"] = str(e)
