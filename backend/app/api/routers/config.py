# backend/app/api/routers/config.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.db.session import get_db_session
from app.services.config_service import get_tenant_full_config, set_tenant_config
from app.api.deps import get_current_tenant, get_current_active_admin

router = APIRouter()


@router.get("/", response_model=Dict[str, Any])
def get_config(db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant)):
    """Get all configuration parameters for the current tenant"""
    return get_tenant_full_config(db, tenant.id)


@router.put("/{key}")
def update_config(key: str, value: Any, db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_active_admin)):  # Only admins can update config
    """Update a configuration parameter for the current tenant"""
    try:
        param = set_tenant_config(db, tenant.id, key, value)
        return {"key": key, "value": param.value}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to update configuration: {str(e)}")
