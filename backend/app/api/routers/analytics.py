# backend/app/api/routers/analytics.py
from fastapi import APIRouter, Depends, Query, Path
from typing import List, Optional
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, Integer

from app.db.session import get_db_session
from app.db.models.prediction import Prediction
from app.db.models.symbol import Symbol
from app.schemas.analytics import DashboardSummary, SymbolPerformance, PredictionTrend, TimeframeEnum, PerformanceMetric
from app.api.deps import get_current_tenant, get_current_user

router = APIRouter()


@router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard_summary(timeframe: TimeframeEnum = Query(TimeframeEnum.MONTH, description="Timeframe for metrics"), db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_user)):
    """Get dashboard summary metrics"""
    today = datetime.now().date()

    # Calculate start date based on timeframe
    if timeframe == TimeframeEnum.DAY:
        start_date = today - timedelta(days=1)
    elif timeframe == TimeframeEnum.WEEK:
        start_date = today - timedelta(days=7)
    elif timeframe == TimeframeEnum.MONTH:
        start_date = today - timedelta(days=30)
    elif timeframe == TimeframeEnum.QUARTER:
        start_date = today - timedelta(days=90)
    elif timeframe == TimeframeEnum.YEAR:
        start_date = today - timedelta(days=365)
    else:  # ALL
        start_date = None

    # Base query for predictions
    base_query = db.query(Prediction).filter(Prediction.tenant_id == tenant.id)
    if start_date:
        base_query = base_query.filter(Prediction.date >= start_date)

    # Get total counts
    total_predictions = base_query.count()
    verified_predictions = base_query.filter(Prediction.verified == True).count()

    # Get recent counts (last 7 days)
    recent_start = today - timedelta(days=7)
    recent_query = db.query(Prediction).filter(Prediction.tenant_id == tenant.id, Prediction.date >= recent_start)
    recent_predictions = recent_query.count()
    recent_verified = recent_query.filter(Prediction.verified == True).count()

    # Get active symbols count
    active_symbols = db.query(func.count(Symbol.id)).filter(Symbol.tenant_id == tenant.id, Symbol.active == True).scalar()

    # Get top performing symbols
    symbol_performance = []
    if start_date:
        # Subquery to get predictions per symbol
        symbol_data = db.query(Prediction.symbol_id, func.count(Prediction.id).label("total"), func.sum(func.cast(Prediction.verified == True, Integer)).label("correct")).filter(Prediction.tenant_id == tenant.id, Prediction.date >= start_date).group_by(Prediction.symbol_id).having(func.count(Prediction.id) >= 5).subquery()

        # Join with symbols to get names
        symbols_with_performance = db.query(Symbol.id, Symbol.name, symbol_data.c.total, symbol_data.c.correct).join(symbol_data, Symbol.id == symbol_data.c.symbol_id).filter(Symbol.tenant_id == tenant.id).all()

        # Calculate performance metrics
        for s in symbols_with_performance:
            accuracy = s.correct / s.total if s.total > 0 else 0
            symbol_performance.append(SymbolPerformance(symbol_id=s.id, symbol_name=s.name, total_predictions=s.total, correct_predictions=s.correct, accuracy=accuracy))

        # Sort by accuracy
        symbol_performance.sort(key=lambda x: x.accuracy, reverse=True)

        # Limit to top 5
        symbol_performance = symbol_performance[:5]

    # Get prediction trends (daily accuracy)
    trends = []
    if start_date:
        # Maximum of 30 data points for the trend
        trend_days = min((today - start_date).days + 1, 30)
        trend_start = today - timedelta(days=trend_days - 1)

        # Get daily counts
        daily_data = db.query(Prediction.date, func.count(Prediction.id).label("total"), func.sum(func.cast(Prediction.verified == True, Integer)).label("correct")).filter(Prediction.tenant_id == tenant.id, Prediction.date >= trend_start).group_by(Prediction.date).order_by(Prediction.date).all()

        # Format trend data
        for day in daily_data:
            accuracy = day.correct / day.total if day.total > 0 else 0
            trends.append(PredictionTrend(date=day.date, total=day.total, correct=day.correct, accuracy=accuracy))

    return DashboardSummary(current_date=today, total_active_symbols=active_symbols, total_predictions=total_predictions, verified_predictions=verified_predictions, overall_accuracy=verified_predictions / total_predictions if total_predictions > 0 else 0, recent_predictions=recent_predictions, recent_accuracy=recent_verified / recent_predictions if recent_predictions > 0 else 0, top_performing_symbols=symbol_performance, prediction_trends=trends)


@router.get("/performance/symbols", response_model=List[SymbolPerformance])
async def get_symbol_performance(timeframe: TimeframeEnum = Query(TimeframeEnum.MONTH, description="Timeframe for metrics"), metric: PerformanceMetric = Query(PerformanceMetric.ACCURACY, description="Sorting metric"), limit: int = Query(10, description="Number of symbols to return"), db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_user)):
    """Get performance metrics for symbols"""
    # Implementation similar to top_performing_symbols in dashboard endpoint
    # with additional sorting options based on metric parameter
    # ...

    # This is a placeholder - implement fully based on your specific requirements
    return []  # Return empty list for now
