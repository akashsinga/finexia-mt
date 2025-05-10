# backend/app/services/prediction_service.py

from sqlalchemy.orm import Session
from sqlalchemy import func, Integer
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
from app.db.models.prediction import Prediction, DirectionEnum
from app.db.models.symbol import Symbol
from app.db.models.tenant import Tenant
from app.core.predict.daily_predictor import predict_for_one_symbol
from app.core.train.daily_trainer import train_model_for_symbol
from app.core.logger import get_logger
import asyncio

logger = get_logger(__name__)


def get_latest_prediction(db: Session, symbol_id: int, tenant_id: int) -> Optional[Prediction]:
    """Get the latest prediction for a specific symbol"""
    return db.query(Prediction).filter(Prediction.symbol_id == symbol_id, Prediction.tenant_id == tenant_id).order_by(Prediction.date.desc()).first()


def get_predictions_by_date(db: Session, tenant_id: int, prediction_date: Optional[date] = None, verified: Optional[bool] = None, direction: Optional[str] = None, min_confidence: float = 0.5, symbol_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[Prediction]:
    """Get predictions with various filters"""
    query = db.query(Prediction).filter(Prediction.tenant_id == tenant_id)

    # Apply filters
    if prediction_date:
        query = query.filter(Prediction.date == prediction_date)

    if verified is not None:
        query = query.filter(Prediction.verified == verified)

    if direction:
        query = query.filter(Prediction.direction_prediction == direction)

    if min_confidence > 0:
        query = query.filter(Prediction.strong_move_confidence >= min_confidence)

    if symbol_id:
        query = query.filter(Prediction.symbol_id == symbol_id)

    # Add pagination
    return query.order_by(Prediction.date.desc()).offset(skip).limit(limit).all()


def create_prediction(db: Session, tenant_id: int, symbol_id: int, data: Dict[str, Any]) -> Prediction:
    """Create a new prediction"""
    # Create prediction object
    prediction = Prediction(tenant_id=tenant_id, symbol_id=symbol_id, date=data.get("date", datetime.now().date()), strong_move_confidence=data.get("strong_move_confidence", 0.0), direction_prediction=data.get("direction_prediction"), direction_confidence=data.get("direction_confidence"), model_config_hash=data.get("model_config_hash", f"{tenant_id}_{datetime.now().date()}"))

    db.add(prediction)
    db.commit()
    db.refresh(prediction)

    return prediction


def update_prediction_verification(db: Session, prediction_id: int, tenant_id: int, verified: bool, actual_move_percent: Optional[float] = None, actual_direction: Optional[str] = None, days_to_fulfill: Optional[int] = None) -> Optional[Prediction]:
    """Update verification status of a prediction"""
    prediction = db.query(Prediction).filter(Prediction.id == prediction_id, Prediction.tenant_id == tenant_id).first()

    if not prediction:
        return None

    prediction.verified = verified

    if verified:
        prediction.verification_date = datetime.now().date()
        prediction.actual_move_percent = actual_move_percent
        prediction.actual_direction = actual_direction
        prediction.days_to_fulfill = days_to_fulfill

    db.commit()
    db.refresh(prediction)

    return prediction


def verify_predictions(db: Session, tenant_id: int) -> int:
    """
    Verify unverified predictions against actual price movements.
    Returns count of predictions updated.
    """
    # Get unverified predictions
    unverified = db.query(Prediction).filter(Prediction.tenant_id == tenant_id, Prediction.verified == False, Prediction.date < datetime.now().date() - timedelta(days=1)).all()

    updated_count = 0

    # Get threshold from tenant's config
    from app.services.config_service import get_tenant_config

    threshold = get_tenant_config(db, tenant_id, "STRONG_MOVE_THRESHOLD")
    threshold = float(threshold) if threshold else 3.0

    max_days = get_tenant_config(db, tenant_id, "MAX_DAYS")
    max_days = int(max_days) if max_days else 5

    for pred in unverified:
        # Get historical prices after prediction date
        prices = db.query(Symbol.trading_symbol, Symbol.exchange).filter(Symbol.id == pred.symbol_id).first()

        if not prices:
            logger.warning(f"Symbol {pred.symbol_id} not found for prediction {pred.id}")
            continue

        # Get EOD prices after prediction date
        from app.db.models.eod_data import EODData

        eod_data = db.query(EODData).filter(EODData.symbol_id == pred.symbol_id, EODData.date > pred.date, EODData.date <= pred.date + timedelta(days=max_days)).order_by(EODData.date.asc()).all()

        if not eod_data:
            logger.warning(f"No EOD data found for verification of prediction {pred.id}")
            continue

        # Get reference price (close on prediction date)
        reference_price = db.query(EODData.close).filter(EODData.symbol_id == pred.symbol_id, EODData.date == pred.date).scalar()

        if not reference_price:
            logger.warning(f"No reference price for prediction {pred.id}")
            continue

        # Calculate maximum up and down moves
        max_up_move, max_down_move = 0, 0
        up_day, down_day = None, None

        for price in eod_data:
            # Calculate up move (high compared to reference)
            up_pct = ((price.high - reference_price) / reference_price) * 100
            if up_pct > max_up_move:
                max_up_move = up_pct
                up_day = price.date

            # Calculate down move (low compared to reference)
            down_pct = ((price.low - reference_price) / reference_price) * 100
            if down_pct < max_down_move:
                max_down_move = down_pct
                down_day = price.date

        # Determine if prediction was verified
        verified = False
        verification_date = None
        days_to_fulfill = None
        actual_move_percent = None
        actual_direction = None

        if pred.direction_prediction == DirectionEnum.UP and max_up_move >= threshold:
            verified = True
            verification_date = up_day
            days_to_fulfill = (up_day - pred.date).days
            actual_move_percent = max_up_move
            actual_direction = DirectionEnum.UP

        elif pred.direction_prediction == DirectionEnum.DOWN and abs(max_down_move) >= threshold:
            verified = True
            verification_date = down_day
            days_to_fulfill = (down_day - pred.date).days
            actual_move_percent = max_down_move
            actual_direction = DirectionEnum.DOWN

        elif max_up_move >= threshold or abs(max_down_move) >= threshold:
            # Move happened but direction was wrong
            verified = False
            if max_up_move > abs(max_down_move):
                actual_move_percent = max_up_move
                actual_direction = DirectionEnum.UP
            else:
                actual_move_percent = max_down_move
                actual_direction = DirectionEnum.DOWN

        # Update prediction record
        if verified or len(eod_data) >= max_days:
            pred.verified = verified
            pred.verification_date = verification_date
            pred.actual_move_percent = actual_move_percent
            pred.actual_direction = actual_direction
            pred.days_to_fulfill = days_to_fulfill
            updated_count += 1

    db.commit()
    return updated_count


async def notify_new_prediction(tenant_id: int, symbol_id: int, prediction_data: Dict[str, Any]):
    """Send notification about a new prediction via WebSocket"""
    from app.websockets.connection_manager import connection_manager

    # Format message
    message = {"type": "prediction", "timestamp": datetime.now().isoformat(), "data": {"tenant_id": tenant_id, "symbol_id": symbol_id, "prediction": prediction_data}, "tenant_id": tenant_id}

    # Send to all clients in predictions topic
    await connection_manager.broadcast(message, "predictions")

    # Also send to tenant-specific channel
    await connection_manager.broadcast_to_tenant(message, tenant_id)


def refresh_prediction(db: Session, tenant_id: int, symbol_id: int, force_retrain: bool = False) -> Optional[Prediction]:
    """
    Force refresh a prediction for a symbol, optionally retraining the model.
    Returns the new prediction if successful.
    """
    # Verify symbol and tenant
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    symbol = db.query(Symbol).filter(Symbol.id == symbol_id).first()

    if not tenant or not symbol:
        logger.error(f"Tenant {tenant_id} or symbol {symbol_id} not found")
        return None

    # Optionally retrain model first
    if force_retrain:
        train_result = train_model_for_symbol(tenant_id, symbol_id)

        if train_result.get("status") != "success":
            logger.error(f"Training failed for tenant {tenant_id}, symbol {symbol_id}")
            return None

    # Generate new prediction
    success = predict_for_one_symbol(tenant_id, symbol_id)
    if not success:
        logger.error(f"Prediction failed for tenant {tenant_id}, symbol {symbol_id}")
        return None

    # Get the newly created prediction
    new_prediction = get_latest_prediction(db, symbol_id, tenant_id)

    # Broadcast via WebSocket if available
    if new_prediction:
        try:
            prediction_dict = {"date": new_prediction.date.isoformat(), "strong_move_confidence": new_prediction.strong_move_confidence, "direction_prediction": new_prediction.direction_prediction, "direction_confidence": new_prediction.direction_confidence}

            # Use create_task to run this asynchronously without blocking
            asyncio.create_task(notify_new_prediction(tenant_id, symbol_id, prediction_dict))
        except Exception as e:
            logger.error(f"WebSocket broadcast error: {str(e)}")

    return new_prediction


def get_prediction_stats(db: Session, tenant_id: int, symbol_id: Optional[int] = None) -> Dict[str, Any]:
    """Get prediction accuracy statistics for a tenant"""
    # Build query
    query = db.query(Prediction).filter(Prediction.tenant_id == tenant_id)

    # Add symbol filter if provided
    if symbol_id:
        query = query.filter(Prediction.symbol_id == symbol_id)

    # Execute query
    predictions = query.all()

    # Calculate metrics
    total_count = len(predictions)
    if total_count == 0:
        return {"total_predictions": 0, "verified_predictions": 0, "accuracy": 0.0, "up_predictions": 0, "down_predictions": 0}

    verified_count = sum(1 for p in predictions if p.verified)
    up_count = sum(1 for p in predictions if p.direction_prediction == DirectionEnum.UP)
    down_count = sum(1 for p in predictions if p.direction_prediction == DirectionEnum.DOWN)

    # Direction accuracy - only for predictions with direction
    direction_predictions = [p for p in predictions if p.direction_prediction and p.actual_direction]
    direction_correct = sum(1 for p in direction_predictions if p.verified and p.direction_prediction == p.actual_direction)

    # Days to fulfill
    days_to_fulfill = [p.days_to_fulfill for p in predictions if p.verified and p.days_to_fulfill]
    avg_days = sum(days_to_fulfill) / len(days_to_fulfill) if days_to_fulfill else None

    return {"totalPredictions": total_count, "verifiedPredictions": verified_count, "accuracy": verified_count / total_count if total_count > 0 else 0.0, "upPredictions": up_count, "downPredictions": down_count, "directionAccuracy": direction_correct / len(direction_predictions) if direction_predictions else None, "avgDaysToFulfill": avg_days}


def get_accuracy_trend(db: Session, tenant_id: int, lookback_days: int = 7, symbol_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get day-by-day prediction accuracy trend for the specified tenant"""
    # Calculate date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=lookback_days * 2)  # Double to account for weekends/holidays

    # Base query grouping by date
    query = db.query(Prediction.date, func.count(Prediction.id).label("total"), func.sum(func.cast(Prediction.verified == True, Integer)).label("correct")).filter(Prediction.tenant_id == tenant_id, Prediction.date >= start_date, Prediction.date <= end_date)

    # Add symbol filter if provided
    if symbol_id:
        query = query.filter(Prediction.symbol_id == symbol_id)

    # Group by date and order by date
    query = query.group_by(Prediction.date).order_by(Prediction.date)

    results = query.all()

    # Format for chart display
    trend_data = []
    for result in results:
        # Skip days with zero predictions
        if result.total == 0:
            continue

        accuracy = (result.correct / result.total) if result.total > 0 else 0
        trend_data.append({"date": result.date.isoformat(), "total": result.total, "correct": result.correct, "accuracy": round(accuracy, 4)})

    # Limit to requested lookback period
    if len(trend_data) > lookback_days:
        trend_data = trend_data[-lookback_days:]

    return trend_data
