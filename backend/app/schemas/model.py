# backend/app/schemas/model.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum


class ModelTypeEnum(str, Enum):
    LIGHTGBM = "lightgbm"
    RANDOM_FOREST = "random_forest"
    XGBOOST = "xgboost"
    NEURAL_NETWORK = "neural_network"


class ModelStatusEnum(str, Enum):
    ACTIVE = "active"
    TRAINING = "training"
    FAILED = "failed"
    INACTIVE = "inactive"


class ModelRequest(BaseModel):
    symbols: Optional[List[int]] = None # List of specific symbol id(s) to train
    model_type: ModelTypeEnum = ModelTypeEnum.LIGHTGBM
    is_active: bool = True
    fo_eligible: bool = True


class ModelStatus(BaseModel):
    id: int
    tenant_id: int
    symbol_id: int
    symbol_name: str
    model_type: ModelTypeEnum
    status: ModelStatusEnum
    created_at: datetime
    last_updated: datetime
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None


class ModelsList(BaseModel):
    models: List[ModelStatus]
    count: int


class ModelTrainingResponse(BaseModel):
    message: str
    model_id: int
    status: str
    estimated_completion: Optional[datetime] = None
