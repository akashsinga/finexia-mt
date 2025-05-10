# app/schemas/watchlist.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class WatchlistItemResponse(BaseModel):
    symbol_id: int
    trading_symbol: str
    name: str
    exchange: str
    fo_eligible: bool
    watchlist_id: int
    priority: int
    notes: Optional[str] = None
    added_at: datetime

    class Config:
        from_attributes = True


class WatchlistItemUpdate(BaseModel):
    priority: Optional[int] = None
    notes: Optional[str] = None


class WatchlistResponse(BaseModel):
    items: List[WatchlistItemResponse]
    count: int


class WatchlistUsageResponse(BaseModel):
    success: bool
    used: int
    max_allowed: Optional[int] = None
    available: Optional[int] = None
    unlimited: bool
