# backend/app/api/routers/symbols.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db_session
from app.schemas.symbol import SymbolCreate, SymbolUpdate, SymbolResponse
from app.services.symbol_service import get_symbol, get_symbols, get_symbol_by_trading_symbol, create_symbol, update_symbol, delete_symbol
from app.api.deps import get_current_tenant, get_current_user, get_current_active_admin

router = APIRouter()


@router.get("", response_model=List[SymbolResponse])
async def list_symbols(active_only: bool = Query(True, description="Only show active symbols"), fo_eligible: Optional[bool] = Query(None, description="Filter by F&O eligibility"), skip: int = Query(0, description="Number of records to skip"), limit: int = Query(100, description="Maximum number of records to return"), db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_user)):
    """List symbols with filtering options"""
    return get_symbols(db, tenant.id, active_only, fo_eligible, skip, limit)


@router.get("/{symbol_id}", response_model=SymbolResponse)
async def get_symbol_by_id(symbol_id: int = Path(..., description="Symbol ID"), db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_user)):
    """Get symbol by ID"""
    db_symbol = get_symbol(db, symbol_id, tenant.id)
    if not db_symbol:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Symbol not found")
    return db_symbol


@router.get("/lookup/{trading_symbol}", response_model=SymbolResponse)
async def lookup_symbol(trading_symbol: str = Path(..., description="Trading symbol"), exchange: str = Query("NSE", description="Exchange code"), db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_user)):
    """Lookup symbol by trading symbol and exchange"""
    db_symbol = get_symbol_by_trading_symbol(db, trading_symbol, exchange, tenant.id)
    if not db_symbol:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Symbol not found")
    return db_symbol


@router.post("/", response_model=SymbolResponse, status_code=status.HTTP_201_CREATED)
async def create_new_symbol(symbol: SymbolCreate, db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_active_admin)):  # Only admins can create symbols
    """Create a new symbol"""
    existing = get_symbol_by_trading_symbol(db, symbol.trading_symbol, symbol.exchange, tenant.id)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Symbol already exists: {symbol.trading_symbol} ({symbol.exchange})")
    return create_symbol(db, symbol, tenant.id)


@router.put("/{symbol_id}", response_model=SymbolResponse)
async def update_symbol_info(symbol_id: int = Path(..., description="Symbol ID"), symbol: SymbolUpdate = None, db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_active_admin)):  # Only admins can update symbols
    """Update a symbol"""
    db_symbol = update_symbol(db, symbol_id, symbol, tenant.id)
    if not db_symbol:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Symbol not found")
    return db_symbol


@router.delete("/{symbol_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_symbol_endpoint(symbol_id: int = Path(..., description="Symbol ID"), db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_active_admin)):  # Only admins can delete symbols
    """Delete a symbol (mark as inactive)"""
    success = delete_symbol(db, symbol_id, tenant.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Symbol not found")
    return None
