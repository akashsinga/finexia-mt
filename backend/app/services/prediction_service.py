# backend/app/services/prediction_service.py
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from app.db.models.prediction import Prediction, DirectionEnum
from app.db.models.symbol import Symbol
from app.db.models.eod_data import EODData
from app.services.config_service import get_tenant_config


def get_latest_prediction(db: Session, symbol_id: int, tenant_id: int) -> Optional[Prediction]:
    """Get the latest prediction for a specific symbol"""
    return db.query(Prediction).filter(Prediction.symbol_id == symbol_id, Prediction.tenant_id == tenant_id).order_by(Prediction.date.desc()).first()


def get_predictions_by_date(db: Session, tenant_id: int, prediction_date: Optional[date] = None, verified: Optional[bool] = None, direction: Optional[str] = None, min_confidence: float = 0.5, skip: int = 0, limit: int = 100) -> List[Prediction]:
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

    # Add pagination
    return query.order_by(Prediction.date.desc()).offset(skip).limit(limit).all()


def create_prediction(db: Session, symbol_id: int, tenant_id: int, data: Dict[str, Any]) -> Prediction:
    """Create a new prediction"""
    # Create prediction object
    prediction = Prediction(symbol_id=symbol_id, tenant_id=tenant_id, date=data.get("date", datetime.now().date()), strong_move_confidence=data.get("strong_move_confidence", 0.0), direction_prediction=data.get("direction_prediction"), direction_confidence=data.get("direction_confidence"), model_config_hash=data.get("model_config_hash"))

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

    for pred in unverified:
        # Get historical prices after prediction date
        prices = db.query(EODData).filter(EODData.tenant_id == tenant_id, EODData.symbol_id == pred.symbol_id, EODData.date > pred.date).order_by(EODData.date.asc()).all()

        if not prices:
            continue

        # Get the threshold from tenant config
        threshold = get_tenant_config(db, tenant_id, "STRONG_MOVE_THRESHOLD")
        if threshold is None:
            threshold = 3.0  # default

        # Get max days to consider from tenant config
        max_days = get_tenant_config(db, tenant_id, "MAX_DAYS")
        if max_days is None:
            max_days = 5  # default

        # Get reference price
        reference_price = db.query(EODData.close).filter(EODData.tenant_id == tenant_id, EODData.symbol_id == pred.symbol_id, EODData.date == pred.date).scalar()

        if not reference_price:
            continue

        # Calculate maximum moves
        max_up_move, max_down_move = 0, 0
        up_day, down_day = None, None

        for i, price in enumerate(prices):
            if i >= max_days:
                break

            # Calculate up move
            up_pct = ((price.high - reference_price) / reference_price) * 100
            if up_pct > max_up_move:
                max_up_move = up_pct
                up_day = price.date

            # Calculate down move
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
        if verified or len(prices) >= max_days:
            pred.verified = verified
            pred.verification_date = verification_date
            pred.actual_move_percent = actual_move_percent
            pred.actual_direction = actual_direction
            pred.days_to_fulfill = days_to_fulfill
            updated_count += 1

    db.commit()
    return updated_count
