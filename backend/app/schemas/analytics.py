# backend/app/schemas/analytics.py
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import date, datetime
from enum import Enum


class TimeframeEnum(str, Enum):
    DAY = "1d"
    WEEK = "1w"
    MONTH = "1m"
    QUARTER = "3m"
    YEAR = "1y"
    ALL = "all"


class PerformanceMetric(str, Enum):
    ACCURACY = "accuracy"
    RETURN = "return"
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"


class PredictionTrend(BaseModel):
    date: date
    total: int
    correct: int
    accuracy: float


class SymbolPerformance(BaseModel):
    symbol_id: int
    symbol_name: str
    total_predictions: int
    correct_predictions: int
    accuracy: float
    avg_return: Optional[float] = None
    win_rate: Optional[float] = None


class DashboardSummary(BaseModel):
    current_date: date
    total_active_symbols: int
    total_predictions: int
    verified_predictions: int
    overall_accuracy: float
    recent_predictions: int
    recent_accuracy: float
    top_performing_symbols: List[SymbolPerformance]
    prediction_trends: List[PredictionTrend]
