# backend/app/schemas/eod_data.py

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date, datetime


class EODImportRequest(BaseModel):
    """Request model for EOD data import"""

    force: bool = False


class EODImportResponse(BaseModel):
    """Response model for EOD data import"""

    message: str
    status: str
    task_id: str
    started_at: str
    websocket_topic: str


class EODDataResponse(BaseModel):
    """EOD data response model"""

    id: int
    symbol_id: int
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    change_percent: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DailyDataPoint(BaseModel):
    """Data point for a specific day"""

    date: str
    count: int
    coverage: float


class MissingSymbol(BaseModel):
    """Symbol with missing data"""

    id: int
    trading_symbol: str
    exchange: str


class EODStatusResponse(BaseModel):
    """Response model for EOD data status check"""

    from_date: str
    to_date: str
    trading_days: int
    active_symbols: int
    total_data_points: int
    ideal_data_points: int
    overall_coverage: float
    data_points_by_day: List[DailyDataPoint]
    symbols_with_missing_data: List[MissingSymbol]
