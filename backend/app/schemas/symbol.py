# backend/app/schemas/symbol.py
from pydantic import BaseModel, Field
from typing import Optional
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
        orm_mode = True


class SymbolResponse(SymbolInDB):
    pass
