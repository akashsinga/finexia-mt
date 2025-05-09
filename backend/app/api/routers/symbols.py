# backend/app/api/routers/symbols.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db_session
from app.schemas.symbol import SymbolResponse
from app.services.symbol_service import get_symbols_for_tenant, get_symbol_for_tenant, get_all_symbols
from app.api.deps import get_current_tenant, get_current_user, get_current_superadmin

router = APIRouter()


@router.get("", response_model=List[SymbolResponse])
async def list_symbols(active_only: bool = Query(True, description="Only show active symbols"), fo_eligible: Optional[bool] = Query(None, description="Filter by F&O eligibility"), skip: int = Query(0, description="Number of records to skip"), limit: int = Query(100, description="Maximum number of records to return"), db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_user)):
    """List symbols for current tenant"""
    return get_symbols_for_tenant(db, tenant.id, active_only, fo_eligible, skip, limit)


@router.get("/all", response_model=List[SymbolResponse])
async def list_all_symbols(active_only: bool = Query(True, description="Only show active symbols"), db: Session = Depends(get_db_session), current_user=Depends(get_current_superadmin)):  # Only superadmins
    """List all symbols across tenants (superadmin only)"""
    return get_all_symbols(db, active_only)


@router.get("/{symbol_id}", response_model=SymbolResponse)
async def get_symbol_by_id(symbol_id: int = Path(..., description="Symbol ID"), db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_user)):
    """Get symbol by ID for current tenant"""
    symbol = get_symbol_for_tenant(db, symbol_id, tenant.id)
    if not symbol:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Symbol not found")
    return symbol
