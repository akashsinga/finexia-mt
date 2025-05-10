# backend/app/api/routers/eod_data.py

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Path, status
from typing import Dict, Any, Optional, List
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
import uuid

from app.db.session import get_db_session
from app.schemas.eod_data import EODImportRequest, EODImportResponse, EODDataResponse, EODStatusResponse
from app.api.deps import get_current_superadmin  # Import dependency for superadmin validation
from app.services.eod_data_service import run_eod_import_task, get_import_status, get_eod_data, check_data_availability, eod_import_status

router = APIRouter()


@router.post("/import", response_model=EODImportResponse)
async def import_eod_data(background_tasks: BackgroundTasks, import_request: EODImportRequest = EODImportRequest(), db: Session = Depends(get_db_session), current_superadmin=Depends(get_current_superadmin)):
    """Import EOD data from external source (superadmin only)"""
    # Generate task ID for tracking
    task_id = str(uuid.uuid4())

    # Get tenant ID from current superadmin
    tenant_id = current_superadmin.tenant_id

    # Initialize the status immediately (before starting the background task)
    eod_import_status[task_id] = {"status": "created", "started_at": datetime.now().isoformat(), "completed_at": None, "result": None, "error": None, "progress": 0, "processed_symbols": 0, "total_symbols": 0}

    # Start background task
    background_tasks.add_task(run_eod_import_task, task_id=task_id, tenant_id=tenant_id, force_download=import_request.force)

    return {"message": "EOD data import started in background", "status": "created", "task_id": task_id, "started_at": datetime.now().isoformat(), "websocket_topic": f"eod_import_{task_id}"}


@router.get("/import/status/{task_id}", response_model=Dict[str, Any])
async def get_eod_import_status(task_id: str = Path(..., description="Import task ID"), current_superadmin=Depends(get_current_superadmin)):  # Only superadmins can check import status
    """
    Get the status of an EOD data import task

    Returns the current status of a previously initiated EOD data import task.
    """
    status = get_import_status(task_id)

    if status.get("status") == "not_found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import task not found")

    return status


@router.get("/availability", response_model=EODStatusResponse)
async def check_eod_data_availability(from_date: Optional[date] = Query(None, description="Start date for checking data availability"), to_date: Optional[date] = Query(None, description="End date for checking data availability"), db: Session = Depends(get_db_session), current_superadmin=Depends(get_current_superadmin)):  # Only superadmins can check data availability
    """
    Check EOD data availability

    This endpoint checks the availability of EOD data in the specified date range.
    It returns statistics on coverage and identifies symbols with missing data.
    """
    return check_data_availability(db, from_date, to_date)


@router.get("/{symbol_id}", response_model=List[EODDataResponse])
async def get_eod_data_for_symbol(symbol_id: int = Path(..., description="Symbol ID"), from_date: Optional[date] = Query(None, description="Start date for EOD data"), to_date: Optional[date] = Query(None, description="End date for EOD data"), limit: int = Query(100, description="Maximum number of records to return"), db: Session = Depends(get_db_session)):
    """
    Get EOD data for a specific symbol

    This endpoint returns EOD data for the specified symbol in the given date range.
    """
    data = get_eod_data(db, symbol_id, from_date, to_date, limit)

    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No EOD data found for symbol {symbol_id} in the specified date range")

    return data
