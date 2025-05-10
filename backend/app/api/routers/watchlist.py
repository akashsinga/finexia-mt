# app/api/routers/watchlist.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from app.db.session import get_db_session
from app.schemas.watchlist import WatchlistResponse, WatchlistItemUpdate, WatchlistUsageResponse
from app.api.deps import get_current_tenant, get_current_user
from app.services.symbol_service import get_tenant_watchlist, add_to_watchlist, remove_from_watchlist, get_watchlist_usage, update_watchlist_item

router = APIRouter()


@router.get("", response_model=WatchlistResponse)
async def get_watchlist(active_only: bool = Query(True, description="Only show active symbols"), db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_user)):
    """Get tenant's watchlist"""
    watchlist = get_tenant_watchlist(db, tenant.id, active_only)
    return WatchlistResponse(items=watchlist, count=len(watchlist))


@router.post("/{symbol_id}", response_model=Dict[str, Any])
async def add_symbol_to_watchlist(symbol_id: int = Path(..., description="Symbol ID to add to watchlist"), priority: int = Query(0, description="Priority in watchlist (higher numbers appear first)"), notes: Optional[str] = Query(None, description="Optional notes about this symbol"), db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_user)):
    """Add symbol to watchlist"""
    result = add_to_watchlist(db, tenant.id, symbol_id, priority, notes)

    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["message"])

    return result


@router.delete("/{symbol_id}", response_model=Dict[str, Any])
async def remove_symbol_from_watchlist(symbol_id: int = Path(..., description="Symbol ID to remove from watchlist"), db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_user)):
    """Remove symbol from watchlist"""
    result = remove_from_watchlist(db, tenant.id, symbol_id)

    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["message"])

    return result


@router.put("/{watchlist_id}", response_model=Dict[str, Any])
async def update_watchlist_item_endpoint(watchlist_id: int = Path(..., description="Watchlist item ID to update"), item: WatchlistItemUpdate = None, db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_user)):
    """Update watchlist item properties (priority, notes)"""
    result = update_watchlist_item(db, tenant.id, watchlist_id, item.priority, item.notes)

    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["message"])

    return result


@router.get("/usage", response_model=WatchlistUsageResponse)
async def get_watchlist_usage_stats(db: Session = Depends(get_db_session), tenant=Depends(get_current_tenant), current_user=Depends(get_current_user)):
    """Get watchlist usage statistics"""
    usage = get_watchlist_usage(db, tenant.id)

    if not usage["success"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=usage["message"])

    return WatchlistUsageResponse(**usage)
