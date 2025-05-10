# app/api/routers/feature_data.py

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Path, status
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import time
from datetime import datetime

from app.db.session import get_db_session
from app.api.deps import get_current_superadmin
from app.services.feature_data_service import calculate_features_for_symbol, get_feature_calculation_status, run_feature_calculation_background

router = APIRouter()


@router.post("/calculate", response_model=Dict[str, Any])
async def trigger_feature_calculation(background_tasks: BackgroundTasks, symbol_ids: Optional[List[int]] = None, active_only: bool = True, db: Session = Depends(get_db_session), current_superadmin=Depends(get_current_superadmin)):  # Only superadmins can trigger calculation
    """
    Trigger calculation of features for all or specified symbols
    """
    # Generate calculation ID
    calculation_id = str(int(time.time()))

    # Start task in background
    background_tasks.add_task(run_feature_calculation_background, calculation_id=calculation_id, symbol_ids=symbol_ids, active_only=active_only)

    return {"message": "Feature calculation started", "calculation_id": calculation_id, "status": "started", "websocket_topic": f"feature_calculation_{calculation_id}"}


@router.get("/status/{calculation_id}", response_model=Dict[str, Any])
async def get_calculation_status(calculation_id: str = Path(..., description="Calculation ID"), current_superadmin=Depends(get_current_superadmin)):  # Only superadmins can check status
    """
    Get the status of a feature calculation task
    """
    status = get_feature_calculation_status(calculation_id)

    if status["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Calculation task not found")

    return status


@router.post("/calculate/{symbol_id}", response_model=Dict[str, Any])
async def calculate_features_for_one_symbol(symbol_id: int = Path(..., description="Symbol ID"), db: Session = Depends(get_db_session), current_superadmin=Depends(get_current_superadmin)):  # Only superadmins can trigger calculation
    """
    Calculate features for a specific symbol
    """
    result = calculate_features_for_symbol(db, symbol_id)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return result


@router.get("/status", response_model=Dict[str, Any])
async def check_feature_data_status(db: Session = Depends(get_db_session), current_superadmin=Depends(get_current_superadmin)):  # Only superadmins can check status
    """
    Check the status of feature data (coverage, missing data, etc.)
    """
    # Query to check feature data status
    query = """
        SELECT 
            COUNT(DISTINCT s.id) AS total_symbols,
            COUNT(DISTINCT f.symbol_id) AS symbols_with_features,
            COUNT(f.id) AS total_features,
            MIN(f.date) AS earliest_date,
            MAX(f.date) AS latest_date
        FROM symbols s
        LEFT JOIN feature_data f ON s.id = f.symbol_id
        WHERE s.active = true
    """

    # Execute query
    from sqlalchemy import text

    result = db.execute(text(query)).first()

    # Calculate missing features
    query_missing = """
        SELECT 
            COUNT(*) AS missing_count
        FROM (
            SELECT e.symbol_id, e.date
            FROM eod_data e
            LEFT JOIN feature_data f ON e.symbol_id = f.symbol_id AND e.date = f.date
            WHERE f.id IS NULL
            AND e.symbol_id IN (SELECT id FROM symbols WHERE active = true)
        ) AS missing
    """

    missing_result = db.execute(text(query_missing)).first()

    # Safely calculate statistics
    total_symbols = result[0] or 0
    symbols_with_features = result[1] or 0
    total_features = result[2] or 0
    earliest_date = result[3].isoformat() if result[3] else None
    latest_date = result[4].isoformat() if result[4] else None
    missing_features = missing_result[0] or 0

    # Calculate coverage
    total_possible = total_features + missing_features
    coverage_percent = (total_features / total_possible) * 100 if total_possible > 0 else 0

    # Prepare response
    status_data = {"total_symbols": total_symbols, "symbols_with_features": symbols_with_features, "total_features": total_features, "earliest_date": earliest_date, "latest_date": latest_date, "missing_features": missing_features, "coverage_percent": coverage_percent}

    return status_data
