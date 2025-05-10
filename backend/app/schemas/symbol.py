# backend/app/schemas/symbol.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime


class SymbolBase(BaseModel):
    trading_symbol: str = Field(..., min_length=1, max_length=20)
    exchange: str = Field(..., min_length=1, max_length=10)
    name: str = Field(..., min_length=1)
    instrument_type: str = Field(...)
    segment: Optional[str] = None
    lot_size: Optional[int] = None
    fo_eligible: bool = False


class SymbolCreate(SymbolBase):
    security_id: str = Field(..., min_length=1)


class SymbolUpdate(BaseModel):
    name: Optional[str] = None
    active: Optional[bool] = None
    fo_eligible: Optional[bool] = None
    lot_size: Optional[int] = None


class SymbolInDB(SymbolBase):
    id: int
    security_id: str
    active: bool
    tenant_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SymbolStatsResponse(BaseModel):
    total_symbols: int
    active_symbols: int
    inactive_symbols: int
    fo_eligible_count: int
    symbols_by_exchange: Dict[str, int]
    recent_updates: int


class SymbolResponse(SymbolInDB):
    pass


# Update in app/schemas/symbol.py


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
