# backend/app/schemas/feature_flags.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class FeatureStatusEnum(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    BETA = "beta"


class FeatureScope(str, Enum):
    GLOBAL = "global"
    TENANT = "tenant"
    USER = "user"


class FeatureFlag(BaseModel):
    id: int
    key: str
    name: str
    description: Optional[str] = None
    status: FeatureStatusEnum
    scope: FeatureScope
    tenant_id: Optional[int] = None
    user_id: Optional[int] = None
    settings: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class FeatureFlagCreate(BaseModel):
    key: str = Field(..., regex=r"^[a-z0-9_]+$")
    name: str
    description: Optional[str] = None
    status: FeatureStatusEnum = FeatureStatusEnum.DISABLED
    scope: FeatureScope = FeatureScope.TENANT
    settings: Optional[Dict[str, Any]] = None


class FeatureFlagUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[FeatureStatusEnum] = None
    settings: Optional[Dict[str, Any]] = None


class FeatureFlagList(BaseModel):
    features: List[FeatureFlag]
    count: int
