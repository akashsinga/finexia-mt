# backend/app/services/symbol_service.py
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.models.symbol import Symbol
from app.schemas.symbol import SymbolCreate, SymbolUpdate


def get_symbol(db: Session, symbol_id: int, tenant_id: int) -> Optional[Symbol]:
    """Get a symbol by ID for a specific tenant"""
    return db.query(Symbol).filter(Symbol.id == symbol_id, Symbol.tenant_id == tenant_id).first()


def get_symbol_by_trading_symbol(db: Session, trading_symbol: str, exchange: str, tenant_id: int) -> Optional[Symbol]:
    """Get a symbol by trading symbol and exchange for a specific tenant"""
    return db.query(Symbol).filter(Symbol.trading_symbol == trading_symbol, Symbol.exchange == exchange, Symbol.tenant_id == tenant_id).first()


def get_symbols(db: Session, tenant_id: int, active_only: bool = True, fo_eligible: Optional[bool] = None, skip: int = 0, limit: int = 100) -> List[Symbol]:
    """Get list of symbols for a specific tenant with filtering"""
    query = db.query(Symbol).filter(Symbol.tenant_id == tenant_id)

    if active_only:
        query = query.filter(Symbol.active)

    if fo_eligible is not None:
        query = query.filter(Symbol.fo_eligible == fo_eligible)

    return query.order_by(Symbol.trading_symbol).offset(skip).limit(limit).all()


def create_symbol(db: Session, symbol: SymbolCreate, tenant_id: int) -> Symbol:
    """Create a new symbol for a specific tenant"""
    db_symbol = Symbol(security_id=symbol.security_id, trading_symbol=symbol.trading_symbol, exchange=symbol.exchange, name=symbol.name, instrument_type=symbol.instrument_type, segment=symbol.segment, lot_size=symbol.lot_size, active=True, fo_eligible=symbol.fo_eligible, tenant_id=tenant_id)

    db.add(db_symbol)
    db.commit()
    db.refresh(db_symbol)

    return db_symbol


def update_symbol(db: Session, symbol_id: int, symbol: SymbolUpdate, tenant_id: int) -> Optional[Symbol]:
    """Update a symbol for a specific tenant"""
    db_symbol = get_symbol(db, symbol_id, tenant_id)
    if not db_symbol:
        return None

    # Update fields if provided
    update_data = symbol.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_symbol, key, value)

    db.commit()
    db.refresh(db_symbol)

    return db_symbol


def delete_symbol(db: Session, symbol_id: int, tenant_id: int) -> bool:
    """Delete a symbol (mark as inactive) for a specific tenant"""
    db_symbol = get_symbol(db, symbol_id, tenant_id)
    if not db_symbol:
        return False

    db_symbol.active = False
    db.commit()

    return True
