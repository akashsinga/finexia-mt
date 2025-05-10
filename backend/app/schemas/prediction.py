# backend/app/schemas/prediction.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date as date_type, datetime
from enum import Enum


class DirectionEnum(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    NONE = "NONE"


class PredictionBase(BaseModel):
    symbol_id: int
    date: date_type
    strong_move_confidence: float = Field(..., ge=0.0, le=1.0)
    direction_prediction: Optional[DirectionEnum] = None
    direction_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class PredictionResponse(PredictionBase):
    id: int
    tenant_id: int
    verified: Optional[bool] = None
    verification_date: Optional[date_type] = None
    actual_move_percent: Optional[float] = None
    actual_direction: Optional[DirectionEnum] = None
    days_to_fulfill: Optional[int] = None
    created_at: datetime
    symbol_name: Optional[str] = None

    class Config:
        from_attributes = True


class PredictionList(BaseModel):
    predictions: List[PredictionResponse]
    count: int


class PredictionFilter(BaseModel):
    date: Optional[date_type] = None
    verified: Optional[bool] = None
    direction: Optional[DirectionEnum] = None
    min_confidence: float = 0.5
    symbol_id: Optional[int] = None
    
    
class PredictionRequest(BaseModel):
    symbols: Optional[List[int]] = None
    is_active: bool = True
    fo_eligible: bool = False

class PredictionStats(BaseModel):
    total_predictions: int
    verified_predictions: int
    accuracy: float
    up_predictions: int
    down_predictions: int
    direction_accuracy: Optional[float] = None
    avg_days_to_fulfill: Optional[float] = None
