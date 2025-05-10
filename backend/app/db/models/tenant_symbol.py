# app/db/models/tenant_symbol.py
from sqlalchemy import Column, Integer, Boolean, ForeignKey, UniqueConstraint, Index, DateTime, String
from sqlalchemy.sql import func
from app.db.base import Base


class TenantSymbol(Base):
    __tablename__ = "tenant_symbols"
    __table_args__ = (
        UniqueConstraint("tenant_id", "symbol_id", name="unique_tenant_symbol"),
        Index("idx_tenant_symbol", "tenant_id", "symbol_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # For ordering in watchlist
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
