# backend/app/services/symbol_service.py
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.models.symbol import Symbol
from app.db.models.tenant_symbol import TenantSymbol


def get_symbols_for_tenant(db: Session, tenant_id: int, active_only: bool = True, fo_eligible: Optional[bool] = None, skip: int = 0, limit: int = 100) -> List[Symbol]:
    """Get symbols available for a specific tenant"""
    query = db.query(Symbol).join(TenantSymbol, Symbol.id == TenantSymbol.symbol_id).filter(TenantSymbol.tenant_id == tenant_id)

    if active_only:
        query = query.filter(Symbol.active == True, TenantSymbol.is_active == True)

    if fo_eligible is not None:
        query = query.filter(Symbol.fo_eligible == fo_eligible)

    return query.order_by(Symbol.trading_symbol).offset(skip).limit(limit).all()


def get_symbol_for_tenant(db: Session, symbol_id: int, tenant_id: int) -> Optional[Symbol]:
    """Get a specific symbol for a tenant"""
    return db.query(Symbol).join(TenantSymbol, Symbol.id == TenantSymbol.symbol_id).filter(Symbol.id == symbol_id, TenantSymbol.tenant_id == tenant_id).first()


# Global symbol operations (for superadmins)
def get_all_symbols(db: Session, active_only: bool = True) -> List[Symbol]:
    """Get all symbols (for superadmins)"""
    query = db.query(Symbol)
    if active_only:
        query = query.filter(Symbol.active == True)
    return query.all()
