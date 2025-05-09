# backend/app/services/tenant_service.py
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate
from fastapi import HTTPException, status
import re


def get_tenant(db: Session, tenant_id: int) -> Optional[Tenant]:
    """Get a tenant by ID"""
    return db.query(Tenant).filter(Tenant.id == tenant_id).first()


def get_tenant_by_slug(db: Session, slug: str) -> Optional[Tenant]:
    """Get a tenant by slug"""
    return db.query(Tenant).filter(Tenant.slug == slug).first()


def get_tenants(db: Session, skip: int = 0, limit: int = 100) -> List[Tenant]:
    """Get all tenants with pagination"""
    return db.query(Tenant).offset(skip).limit(limit).all()


def create_tenant(db: Session, tenant: TenantCreate) -> Tenant:
    """Create a new tenant"""
    # Check if tenant with same slug already exists
    existing = get_tenant_by_slug(db, tenant.slug)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Tenant with slug '{tenant.slug}' already exists")

    # Create tenant
    db_tenant = Tenant(name=tenant.name, slug=tenant.slug, plan=tenant.plan, max_symbols=tenant.max_symbols, is_active=True)

    db.add(db_tenant)
    db.commit()
    db.refresh(db_tenant)

    # Initialize default config for the tenant
    from app.services.config_service import initialize_tenant_config

    initialize_tenant_config(db, db_tenant.id)

    return db_tenant


def update_tenant(db: Session, tenant_id: int, tenant_data: TenantUpdate) -> Optional[Tenant]:
    """Update a tenant"""
    db_tenant = get_tenant(db, tenant_id)
    if not db_tenant:
        return None

    # Update tenant fields
    update_data = tenant_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_tenant, key, value)

    db.commit()
    db.refresh(db_tenant)
    return db_tenant


def delete_tenant(db: Session, tenant_id: int) -> bool:
    """Mark a tenant as inactive (soft delete)"""
    db_tenant = get_tenant(db, tenant_id)
    if not db_tenant:
        return False

    db_tenant.is_active = False
    db.commit()
    return True
