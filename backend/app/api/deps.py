# backend/app/api/deps.py
from fastapi import Depends, Request, HTTPException, status
from app.db.session import get_db_session


async def get_current_tenant(request: Request):
    """Get the current tenant from request state"""
    tenant = getattr(request.state, "tenant", None)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant context required for this operation")
    return tenant
