# backend/app/api/routers/system.py (updated with pipeline integration)
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db_session
from app.db.models.prediction import Prediction
from app.db.models.symbol import Symbol
from app.db.models.tenant import Tenant
from app.schemas.system import SystemStatusResponse, PipelineRunRequest, PipelineRunResponse
from app.api.deps import get_current_tenant, get_current_user, get_current_active_admin
from app.services.pipeline_service import run_pipeline, get_pipeline_status

router = APIRouter()


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status(db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_user)):
    """Get current system status and statistics"""
    # Get basic stats
    total_predictions = db.query(func.count(Prediction.id)).filter(Prediction.tenant_id == tenant.id).scalar() or 0

    today = datetime.now().date()
    today_predictions = db.query(func.count(Prediction.id)).filter(Prediction.tenant_id == tenant.id, Prediction.date == today).scalar() or 0

    verified_predictions = db.query(func.count(Prediction.id)).filter(Prediction.tenant_id == tenant.id, Prediction.verified == True).scalar() or 0

    symbols_count = db.query(func.count(Symbol.id)).filter(Symbol.tenant_id == tenant.id, Symbol.active == True).scalar() or 0

    return SystemStatusResponse(status="online", server_time=datetime.now(), database_status="connected", total_predictions=total_predictions, today_predictions=today_predictions, verified_predictions=verified_predictions, verification_rate=verified_predictions / total_predictions if total_predictions > 0 else 0.0, tenant_id=tenant.id, tenant_name=tenant.name, symbols_count=symbols_count)


@router.post("/run-pipeline", response_model=PipelineRunResponse)
async def trigger_pipeline(background_tasks: BackgroundTasks, request: PipelineRunRequest = PipelineRunRequest(), db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_active_admin)):
    """Trigger a run of the data pipeline for this tenant"""
    # Get current pipeline status
    status = get_pipeline_status(tenant.id)

    # If pipeline is already running and not forced, return status
    if status["status"] == "running" and not request.force:
        return PipelineRunResponse(message="Pipeline already running", started_at=datetime.fromisoformat(status["started_at"]) if isinstance(status["started_at"], str) else status["started_at"], requested_by=current_user.username, status=status["status"])

    # Start pipeline in background task
    background_tasks.add_task(run_pipeline, tenant_id=tenant.id, steps=request.steps, force=request.force)

    return PipelineRunResponse(message="Pipeline started successfully", started_at=datetime.now(), requested_by=current_user.username, status="running")


@router.get("/pipeline-status", response_model=Dict[str, Any])
async def get_pipeline_current_status(db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_user)):
    """Get current pipeline status"""
    return get_pipeline_status(tenant.id)
