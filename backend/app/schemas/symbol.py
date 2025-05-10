# app/schemas/symbol.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# Base symbol model
class SymbolBase(BaseModel):
    trading_symbol: str = Field(..., min_length=1, max_length=20)
    exchange: str = Field(..., min_length=1, max_length=10)
    name: str = Field(..., min_length=1)
    instrument_type: str = Field(...)
    segment: Optional[str] = None
    lot_size: Optional[int] = None
    fo_eligible: bool = False


# Response model for a single symbol
class SymbolResponse(SymbolBase):
    id: int
    security_id: str
    active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Response model for a list of symbols
class SymbolList(BaseModel):
    symbols: List[SymbolResponse]
    count: int


# Models for statistics
class PopularSymbol(BaseModel):
    symbol_id: int
    trading_symbol: str
    name: str
    watchlist_count: int


class WatchlistUsageStats(BaseModel):
    total_symbols_in_watchlists: int
    popular_symbols: List[PopularSymbol]


class SymbolStatsResponse(BaseModel):
    total_symbols: int
    active_symbols: int
    inactive_symbols: int
    fo_eligible_count: int
    symbols_by_exchange: Dict[str, int]
    recent_updates: int
    watchlist_usage: WatchlistUsageStats
