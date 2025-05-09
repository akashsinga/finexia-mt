# backend/app/schemas/tenant.py
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import re


class TenantBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=50)
    plan: str = Field(default="basic")
    max_symbols: Optional[int] = Field(default=None)

    @validator("slug")
    def validate_slug(cls, v):
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
        return v


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    plan: Optional[str] = None
    max_symbols: Optional[int] = Field(None, ge=1, le=1000)
    is_active: Optional[bool] = None


class TenantInDB(TenantBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class TenantResponse(TenantInDB):
    pass
