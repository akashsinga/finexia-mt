# backend/app/services/eod_data_service.py
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Tuple
from datetime import date
import pandas as pd
from app.db.models.eod_data import EODData
from app.db.models.symbol import Symbol


def get_latest_eod_date(db: Session, symbol_id: int, tenant_id: int) -> Optional[date]:
    """Get the latest EOD date for a specific symbol"""
    result = db.query(EODData.date).filter(EODData.symbol_id == symbol_id, EODData.tenant_id == tenant_id).order_by(EODData.date.desc()).first()

    return result[0] if result else None


def import_eod_data(db: Session, symbol_id: int, tenant_id: int, data: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Import EOD data for a specific symbol

    Returns:
        Tuple of (inserted_count, updated_count)
    """
    inserted, updated = 0, 0

    for item in data:
        # Check if record already exists
        existing = db.query(EODData).filter(EODData.symbol_id == symbol_id, EODData.tenant_id == tenant_id, EODData.date == item["date"]).first()

        # Calculate change percent if previous close exists
        change_percent = None
        if "prev_close" in item and item["prev_close"]:
            if item["close"] and item["prev_close"] > 0:
                change_percent = ((item["close"] - item["prev_close"]) / item["prev_close"]) * 100

        if existing:
            # Update existing record
            existing.open = item["open"]
            existing.high = item["high"]
            existing.low = item["low"]
            existing.close = item["close"]
            existing.volume = item["volume"]
            existing.change_percent = change_percent
            updated += 1
        else:
            # Create new record
            new_record = EODData(symbol_id=symbol_id, tenant_id=tenant_id, date=item["date"], open=item["open"], high=item["high"], low=item["low"], close=item["close"], volume=item["volume"], change_percent=change_percent)
            db.add(new_record)
            inserted += 1

    db.commit()
    return inserted, updated


def import_eod_data_from_dataframe(db: Session, symbol_id: int, tenant_id: int, df: pd.DataFrame) -> Tuple[int, int]:
    """Import EOD data from a pandas DataFrame"""
    # Convert DataFrame to list of dicts
    records = df.to_dict("records")

    # Import the records
    return import_eod_data(db, symbol_id, tenant_id, records)


def get_eod_data(db: Session, symbol_id: int, tenant_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None, limit: int = 100) -> List[EODData]:
    """Get EOD data for a specific symbol with date range filtering"""
    query = db.query(EODData).filter(EODData.symbol_id == symbol_id, EODData.tenant_id == tenant_id)

    if start_date:
        query = query.filter(EODData.date >= start_date)

    if end_date:
        query = query.filter(EODData.date <= end_date)

    # Order by date descending (newest first)
    query = query.order_by(EODData.date.desc())

    # Apply limit
    return query.limit(limit).all()
