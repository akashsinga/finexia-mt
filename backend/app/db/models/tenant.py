# backend/app/db/models/tenant.py (updated)
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    plan = Column(String, default="basic")  # basic, premium, enterprise
    max_symbols = Column(Integer, default=20)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Override the tenant_id field since Tenant doesn't have a tenant
    tenant_id = None

    # Relationships
    users = relationship("User", back_populates="tenant")
