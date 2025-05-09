# backend/app/api/routers/tenants.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db_session
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from app.services.tenant_service import create_tenant, get_tenant, get_tenants, update_tenant, delete_tenant
from app.api.deps import get_current_superadmin

router = APIRouter()


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def create_new_tenant(tenant: TenantCreate, db: Session = Depends(get_db_session), current_user=Depends(get_current_superadmin)):  # Only superadmins can create tenants
    """Create a new tenant"""
    return create_tenant(db, tenant)


@router.get("", response_model=List[TenantResponse])
def read_tenants(skip: int = 0, limit: int = 100, db: Session = Depends(get_db_session), current_user=Depends(get_current_superadmin)):  # Only superadmins can list all tenants
    """Get all tenants"""
    return get_tenants(db, skip, limit)


@router.get("/{tenant_id}", response_model=TenantResponse)
def read_tenant(tenant_id: int, db: Session = Depends(get_db_session), current_user=Depends(get_current_superadmin)):  # Only superadmins can get tenant details
    """Get a specific tenant"""
    tenant = get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant


@router.put("/{tenant_id}", response_model=TenantResponse)
def update_tenant_endpoint(tenant_id: int, tenant_data: TenantUpdate, db: Session = Depends(get_db_session), current_user=Depends(get_current_superadmin)):  # Only superadmins can update tenants
    """Update a tenant"""
    tenant = update_tenant(db, tenant_id, tenant_data)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant_endpoint(tenant_id: int, db: Session = Depends(get_db_session), current_user=Depends(get_current_superadmin)):  # Only superadmins can delete tenants
    """Delete a tenant (soft delete)"""
    success = delete_tenant(db, tenant_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return None
