# app/services/symbol_service.py
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from sqlalchemy import func, or_
from app.db.models.symbol import Symbol
from app.db.models.tenant_symbol import TenantSymbol
from app.db.models.tenant import Tenant


# Symbol Access (All Users)
def get_symbols(db: Session, active_only: bool = True, fo_eligible: Optional[bool] = None, skip: int = 0, limit: int = 100) -> List[Symbol]:
    """Get all symbols with optional filtering"""
    query = db.query(Symbol)

    if active_only:
        query = query.filter(Symbol.active == True)

    if fo_eligible is not None:
        query = query.filter(Symbol.fo_eligible == fo_eligible)

    return query.order_by(Symbol.trading_symbol).offset(skip).limit(limit).all()


def get_symbol_by_id(db: Session, symbol_id: int) -> Optional[Symbol]:
    """Get a specific symbol by ID"""
    return db.query(Symbol).filter(Symbol.id == symbol_id).first()


def search_symbols(db: Session, search_term: str, active_only: bool = True) -> List[Symbol]:
    """Search symbols by name or trading symbol"""
    query = db.query(Symbol)

    if active_only:
        query = query.filter(Symbol.active == True)

    search_pattern = f"%{search_term}%"
    query = query.filter(or_(Symbol.trading_symbol.ilike(search_pattern), Symbol.name.ilike(search_pattern)))

    return query.order_by(Symbol.trading_symbol).limit(20).all()


# Watchlist Management
def get_tenant_watchlist(db: Session, tenant_id: int, active_only: bool = True, fo_eligible = False) -> List[Dict[str, Any]]:
    """Get symbols in tenant's watchlist"""
    query = db.query(Symbol, TenantSymbol).join(TenantSymbol, Symbol.id == TenantSymbol.symbol_id).filter(TenantSymbol.tenant_id == tenant_id)

    if active_only:
        query = query.filter(Symbol.active == True, TenantSymbol.is_active == True)
    
    if fo_eligible:
        query = query.filter(Symbol.fo_eligible)

    query = query.order_by(TenantSymbol.priority.desc(), Symbol.trading_symbol)

    result = []
    for symbol, tenant_symbol in query.all():
        result.append({"symbol_id": symbol.id, "trading_symbol": symbol.trading_symbol, "name": symbol.name, "exchange": symbol.exchange, "fo_eligible": symbol.fo_eligible, "watchlist_id": tenant_symbol.id, "priority": tenant_symbol.priority, "notes": tenant_symbol.notes, "added_at": tenant_symbol.created_at})

    return result


def add_to_watchlist(db: Session, tenant_id: int, symbol_id: int, priority: int = 0, notes: Optional[str] = None) -> Dict[str, Any]:
    """Add symbol to tenant's watchlist with plan limit check"""
    # Check if symbol exists
    symbol = db.query(Symbol).filter(Symbol.id == symbol_id, Symbol.active == True).first()
    if not symbol:
        return {"success": False, "message": "Symbol not found or inactive"}

    # Check if symbol is already in watchlist
    existing = db.query(TenantSymbol).filter(TenantSymbol.tenant_id == tenant_id, TenantSymbol.symbol_id == symbol_id).first()

    if existing:
        if existing.is_active:
            return {"success": False, "message": "Symbol already in watchlist"}
        else:
            # Reactivate existing entry
            existing.is_active = True
            existing.priority = priority
            existing.notes = notes
            db.commit()
            return {"success": True, "message": "Symbol reactivated in watchlist"}

    # Check plan limits
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        return {"success": False, "message": "Tenant not found"}

    # Count active symbols in watchlist
    active_count = db.query(func.count(TenantSymbol.id)).filter(TenantSymbol.tenant_id == tenant_id, TenantSymbol.is_active == True).scalar()

    # Check if adding would exceed limit
    if tenant.max_symbols is not None and active_count >= tenant.max_symbols:
        return {"success": False, "message": f"Plan limit reached. Maximum {tenant.max_symbols} symbols allowed."}

    # Add to watchlist
    tenant_symbol = TenantSymbol(tenant_id=tenant_id, symbol_id=symbol_id, is_active=True, priority=priority, notes=notes)
    db.add(tenant_symbol)
    db.commit()
    db.refresh(tenant_symbol)

    return {"success": True, "message": "Symbol added to watchlist", "watchlist_id": tenant_symbol.id}


def remove_from_watchlist(db: Session, tenant_id: int, symbol_id: int) -> Dict[str, bool]:
    """Remove symbol from tenant's watchlist"""
    # Find the entry
    entry = db.query(TenantSymbol).filter(TenantSymbol.tenant_id == tenant_id, TenantSymbol.symbol_id == symbol_id, TenantSymbol.is_active == True).first()

    if not entry:
        return {"success": False, "message": "Symbol not found in watchlist"}

    # Mark as inactive
    entry.is_active = False
    db.commit()

    return {"success": True, "message": "Symbol removed from watchlist"}


def get_watchlist_usage(db: Session, tenant_id: int) -> Dict[str, Any]:
    """Get watchlist usage statistics"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        return {"success": False, "message": "Tenant not found"}

    total_count = db.query(func.count(TenantSymbol.id)).filter(TenantSymbol.tenant_id == tenant_id, TenantSymbol.is_active == True).scalar()

    max_allowed = tenant.max_symbols

    return {"success": True, "used": total_count, "max_allowed": max_allowed, "available": (max_allowed - total_count) if max_allowed is not None else None, "unlimited": max_allowed is None}


def check_symbol_in_watchlist(db: Session, tenant_id: int, symbol_id: int) -> bool:
    """Check if a symbol is in tenant's watchlist (for other services)"""
    entry = db.query(TenantSymbol).filter(TenantSymbol.tenant_id == tenant_id, TenantSymbol.symbol_id == symbol_id, TenantSymbol.is_active == True).first()

    return entry is not None


def update_watchlist_item(db: Session, tenant_id: int, watchlist_id: int, priority: Optional[int] = None, notes: Optional[str] = None) -> Dict[str, Any]:
    """Update a watchlist item's properties"""
    # Find the entry
    entry = db.query(TenantSymbol).filter(TenantSymbol.id == watchlist_id, TenantSymbol.tenant_id == tenant_id, TenantSymbol.is_active == True).first()

    if not entry:
        return {"success": False, "message": "Watchlist item not found"}

    # Update fields if provided
    if priority is not None:
        entry.priority = priority

    if notes is not None:
        entry.notes = notes

    db.commit()

    return {"success": True, "message": "Watchlist item updated", "watchlist_id": entry.id}


def get_symbols_with_stats(db: Session) -> Dict[str, Any]:
    """Get system-wide symbol statistics for admin dashboard"""
    # Total symbols
    total_symbols = db.query(func.count(Symbol.id)).scalar()

    # Active symbols
    active_symbols = db.query(func.count(Symbol.id)).filter(Symbol.active == True).scalar()

    # Inactive symbols
    inactive_symbols = total_symbols - active_symbols

    # F&O eligible symbols
    fo_eligible_count = db.query(func.count(Symbol.id)).filter(Symbol.fo_eligible == True).scalar()

    # Symbols by exchange
    exchange_counts = {}
    for exchange, count in db.query(Symbol.exchange, func.count(Symbol.id)).group_by(Symbol.exchange).all():
        exchange_counts[exchange] = count

    # Recently updated symbols (last 7 days)
    from datetime import datetime, timedelta

    one_week_ago = datetime.now() - timedelta(days=7)
    recent_updates = db.query(func.count(Symbol.id)).filter(Symbol.updated_at >= one_week_ago).scalar()

    # Symbols in watchlists
    watchlist_count = db.query(func.count(func.distinct(TenantSymbol.symbol_id))).filter(TenantSymbol.is_active == True).scalar()

    # Most popular symbols in watchlists
    popular_symbols_query = db.query(Symbol.id, Symbol.trading_symbol, Symbol.name, func.count(TenantSymbol.id).label("watchlist_count")).join(TenantSymbol, Symbol.id == TenantSymbol.symbol_id).filter(TenantSymbol.is_active == True).group_by(Symbol.id, Symbol.trading_symbol, Symbol.name).order_by(func.count(TenantSymbol.id).desc()).limit(10)

    popular_symbols = [{"symbol_id": s.id, "trading_symbol": s.trading_symbol, "name": s.name, "watchlist_count": s.watchlist_count} for s in popular_symbols_query.all()]

    return {"total_symbols": total_symbols, "active_symbols": active_symbols, "inactive_symbols": inactive_symbols, "fo_eligible_count": fo_eligible_count, "symbols_by_exchange": exchange_counts, "recent_updates": recent_updates, "watchlist_usage": {"total_symbols_in_watchlists": watchlist_count, "popular_symbols": popular_symbols}}
