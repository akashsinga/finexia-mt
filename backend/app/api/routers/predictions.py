# backend/app/api/routers/predictions.py
from fastapi import APIRouter, HTTPException, Path, Query, Depends, status, BackgroundTasks
from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.db.models.prediction import Prediction, DirectionEnum
from app.db.models.symbol import Symbol
from app.schemas.prediction import PredictionResponse, PredictionList, PredictionFilter, PredictionStats, PredictionRequest
from app.services.prediction_service import get_latest_prediction, get_predictions_by_date, verify_predictions
from app.core.predict.daily_predictor import predict_for_tenant
from app.api.deps import get_current_tenant, get_current_user, get_current_active_admin

router = APIRouter()


@router.get("/symbol/{symbol_id}", response_model=PredictionResponse)
async def get_prediction_for_symbol(symbol_id: int = Path(..., description="Symbol ID"), db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_user)):
    """Get latest prediction for a specific symbol"""
    prediction = get_latest_prediction(db, symbol_id, tenant.id)
    if not prediction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No prediction found for symbol {symbol_id}")

    # Add symbol name for convenience
    symbol = db.query(Symbol).filter(Symbol.id == symbol_id, Symbol.tenant_id == tenant.id).first()
    prediction_dict = {**prediction.__dict__, "symbol_name": symbol.name if symbol else None}

    return prediction_dict


@router.get("", response_model=PredictionList)
async def list_predictions(date: Optional[date] = Query(None, description="Filter by prediction date"), verified: Optional[bool] = Query(None, description="Filter by verification status"), direction: Optional[str] = Query(None, description="Filter by direction (UP/DOWN)"), min_confidence: float = Query(0.5, description="Minimum confidence threshold"), symbol_id: Optional[int] = Query(None, description="Filter by symbol ID"), skip: int = Query(0, description="Number of records to skip"), limit: int = Query(100, description="Maximum number of records to return"), db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_user)):
    """Get predictions with various filters"""
    filters = PredictionFilter(date=date, verified=verified, direction=direction, min_confidence=min_confidence, symbol_id=symbol_id)

    predictions = get_predictions_by_date(db, tenant.id, filters, skip, limit)

    # Enrich with symbol names
    symbol_ids = [p.symbol_id for p in predictions]
    symbols = {s.id: s.name for s in db.query(Symbol).filter(Symbol.id.in_(symbol_ids), Symbol.tenant_id == tenant.id).all()}

    enriched_predictions = []
    for p in predictions:
        p_dict = {**p.__dict__}
        p_dict["symbol_name"] = symbols.get(p.symbol_id)
        enriched_predictions.append(p_dict)

    return PredictionList(predictions=enriched_predictions, count=len(enriched_predictions))


@router.get("/stats", response_model=PredictionStats)
async def get_prediction_stats(start_date: Optional[date] = Query(None, description="Start date for stats period"), end_date: Optional[date] = Query(None, description="End date for stats period"), symbol_id: Optional[int] = Query(None, description="Filter by symbol ID"), db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_user)):
    """Get prediction accuracy statistics"""
    query = db.query(Prediction).filter(Prediction.tenant_id == tenant.id)

    if start_date:
        query = query.filter(Prediction.date >= start_date)

    if end_date:
        query = query.filter(Prediction.date <= end_date)

    if symbol_id:
        query = query.filter(Prediction.symbol_id == symbol_id)

    predictions = query.all()

    # Calculate statistics
    total_count = len(predictions)
    verified_count = sum(1 for p in predictions if p.verified)
    up_count = sum(1 for p in predictions if p.direction_prediction == DirectionEnum.UP)
    down_count = sum(1 for p in predictions if p.direction_prediction == DirectionEnum.DOWN)

    # Direction accuracy
    direction_predictions = [p for p in predictions if p.verified and p.direction_prediction and p.actual_direction]
    direction_correct = sum(1 for p in direction_predictions if p.direction_prediction == p.actual_direction)

    # Days to fulfill
    days_to_fulfill = [p.days_to_fulfill for p in predictions if p.verified and p.days_to_fulfill]

    return PredictionStats(total_predictions=total_count, verified_predictions=verified_count, accuracy=verified_count / total_count if total_count > 0 else 0.0, up_predictions=up_count, down_predictions=down_count, direction_accuracy=direction_correct / len(direction_predictions) if direction_predictions else None, avg_days_to_fulfill=sum(days_to_fulfill) / len(days_to_fulfill) if days_to_fulfill else None)


@router.post("/verify", status_code=status.HTTP_200_OK)
async def run_prediction_verification(db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_active_admin)):
    """Manually verify predictions against actual price movements"""
    updated_count = verify_predictions(db, tenant.id)
    return {"message": f"Verified {updated_count} predictions"}


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_predictions(background_tasks: BackgroundTasks, request: Optional[PredictionRequest] = None, db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_user)):
    """Generate predictions for symbols"""

    background_tasks.add_tassk(predict_for_tenant, tenant.id, request, current_user)

    return {"message": "Prediction generation started", "status": "processing", "tenant_id": tenant.id, "symbols_count": len(request.symbols) if request.symbols else "all watchlist symbols", "requested_by": current_user.username}
