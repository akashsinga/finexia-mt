# backend/app/services/pipeline_service.py

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import logging
from app.core.logger import get_logger

logger = get_logger(__name__)


class PipelineStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStep:
    DATA_IMPORT = "data_import"
    FEATURE_ENGINEERING = "feature_engineering"
    MODEL_TRAINING = "model_training"
    PREDICTION_GENERATION = "prediction_generation"
    VERIFICATION = "verification"


# In-memory tracking of pipeline status by tenant
_pipeline_status = {}


def get_pipeline_status(tenant_id: int) -> Dict[str, Any]:
    """Get current pipeline status for a tenant"""
    if tenant_id not in _pipeline_status:
        return {"status": PipelineStatus.COMPLETED, "current_step": None, "progress": 1.0, "message": "No pipeline running", "started_at": None, "updated_at": None}

    return _pipeline_status[tenant_id]


def update_pipeline_status(tenant_id: int, status: str, current_step: Optional[str] = None, progress: float = 0.0, message: str = ""):
    """Update pipeline status and send notification"""
    _pipeline_status[tenant_id] = {"status": status, "current_step": current_step, "progress": progress, "message": message, "started_at": _pipeline_status.get(tenant_id, {}).get("started_at", datetime.now()), "updated_at": datetime.now()}

    # Send WebSocket notification asynchronously
    asyncio.create_task(notify_pipeline_status(tenant_id, status, progress, message))

    return _pipeline_status[tenant_id]


async def notify_pipeline_status(tenant_id: int, status: str, progress: float, message: str):
    """Send notification about pipeline status via WebSocket"""
    from app.websockets.connection_manager import connection_manager

    # Format message
    websocket_message = {"type": "pipeline_status", "timestamp": datetime.now().isoformat(), "data": {"status": status, "progress": progress, "message": message}, "tenant_id": tenant_id}

    # Send to pipeline topic
    await connection_manager.broadcast(websocket_message, "pipeline")

    # Also send to tenant-specific channel
    await connection_manager.broadcast_to_tenant(websocket_message, tenant_id)


async def run_pipeline(tenant_id: int, steps: Optional[List[str]] = None, force: bool = False) -> Dict[str, Any]:
    """Run the data pipeline for a tenant"""
    # Check if pipeline is already running
    current_status = get_pipeline_status(tenant_id)
    if current_status["status"] == PipelineStatus.RUNNING and not force:
        return {"message": "Pipeline already running", "status": current_status["status"], "started_at": current_status["started_at"]}

    # Update status to running
    update_pipeline_status(tenant_id=tenant_id, status=PipelineStatus.RUNNING, current_step=None, progress=0.0, message="Pipeline started")

    try:
        # Determine steps to run
        pipeline_steps = steps or [PipelineStep.DATA_IMPORT, PipelineStep.FEATURE_ENGINEERING, PipelineStep.MODEL_TRAINING, PipelineStep.PREDICTION_GENERATION, PipelineStep.VERIFICATION]

        total_steps = len(pipeline_steps)
        completed_steps = 0

        # For each step
        for step in pipeline_steps:
            # Update status with current step
            update_pipeline_status(tenant_id=tenant_id, status=PipelineStatus.RUNNING, current_step=step, progress=completed_steps / total_steps, message=f"Running step: {step}")

            # Run the appropriate step function
            if step == PipelineStep.DATA_IMPORT:
                # Import data (EOD data is tenant-agnostic, so this step is just informational)
                logger.info(f"Data import step for tenant {tenant_id}")
                await asyncio.sleep(2)  # Simulating work

            elif step == PipelineStep.FEATURE_ENGINEERING:
                # Process features (features are tenant-agnostic)
                logger.info(f"Feature engineering step for tenant {tenant_id}")
                await asyncio.sleep(3)  # Simulating work

            elif step == PipelineStep.MODEL_TRAINING:
                # Train tenant-specific models
                logger.info(f"Model training step for tenant {tenant_id}")
                # This would call the actual training function
                from app.core.train.daily_trainer import train_models_for_tenant

                # Run in thread to avoid blocking
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: train_models_for_tenant(tenant_id))

                # Check result and log
                success_count = sum(1 for r in result.values() if r.get("status") == "success")
                total_count = len(result)
                logger.info(f"Trained {success_count}/{total_count} models for tenant {tenant_id}")

            elif step == PipelineStep.PREDICTION_GENERATION:
                # Generate tenant-specific predictions
                logger.info(f"Prediction generation step for tenant {tenant_id}")
                # This would call the actual prediction function
                from app.core.predict.daily_predictor import predict_for_tenant

                # Run in thread to avoid blocking
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: predict_for_tenant(tenant_id))

                # Check result and log
                success_count = sum(1 for success in result.values() if success)
                total_count = len(result)
                logger.info(f"Generated {success_count}/{total_count} predictions for tenant {tenant_id}")

            elif step == PipelineStep.VERIFICATION:
                # Verify tenant-specific predictions
                logger.info(f"Verification step for tenant {tenant_id}")
                await asyncio.sleep(1)  # Simulating work - would call actual verification

            # Update progress
            completed_steps += 1
            update_pipeline_status(tenant_id=tenant_id, status=PipelineStatus.RUNNING, current_step=step, progress=completed_steps / total_steps, message=f"Completed step: {step}")

        # Update status to completed
        update_pipeline_status(tenant_id=tenant_id, status=PipelineStatus.COMPLETED, current_step=None, progress=1.0, message="Pipeline completed successfully")

        return {"message": "Pipeline completed successfully", "status": PipelineStatus.COMPLETED, "steps_executed": pipeline_steps}

    except Exception as e:
        logger.error(f"Pipeline error for tenant {tenant_id}: {str(e)}")

        # Update status to failed
        update_pipeline_status(tenant_id=tenant_id, status=PipelineStatus.FAILED, current_step=None, progress=0.0, message=f"Pipeline failed: {str(e)}")

        return {"message": f"Pipeline failed: {str(e)}", "status": PipelineStatus.FAILED}
