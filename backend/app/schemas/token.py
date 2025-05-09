# backend/app/schemas/token.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime
    tenant_slug: Optional[str] = None


class TokenData(BaseModel):
    username: Optional[str] = None
