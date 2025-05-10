# app/services/feature_data_service.py

from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from datetime import date, datetime, timedelta
import time
from app.db.models.symbol import Symbol
from app.db.models.feature_data import FeatureData
from app.core.features.feature_engineer import calculate_features
from app.core.logger import get_logger
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
from app.websockets.connection_manager import connection_manager
import asyncio

logger = get_logger(__name__)

# In-memory tracking for feature calculation status
feature_calculation_status = {}


async def notify_feature_calculation_status(calculation_id: str, status: str, details: Dict[str, Any] = None):
    """Send WebSocket notification about feature calculation status"""
    message = {"type": "feature_calculation_status", "timestamp": datetime.now().isoformat(), "data": {"calculation_id": calculation_id, "status": status, **(details or {})}}

    # Broadcast to specific topic
    await connection_manager.broadcast(message, f"feature_calculation_{calculation_id}")

    # Also broadcast to features topic
    await connection_manager.broadcast(message, "features")


def get_latest_feature_date(db: Session, symbol_id: int) -> Optional[date]:
    """Get the latest feature date for a symbol"""
    result = db.query(func.max(FeatureData.date)).filter(FeatureData.symbol_id == symbol_id).first()
    return result[0] if result and result[0] else None


def get_missing_feature_dates(db: Session, symbol_id: int) -> List[date]:
    """Get dates that have EOD data but no corresponding feature data"""
    query = """
        SELECT e.date
        FROM eod_data e
        LEFT JOIN feature_data f ON e.symbol_id = f.symbol_id AND e.date = f.date
        WHERE e.symbol_id = :symbol_id
        AND f.id IS NULL
        ORDER BY e.date
    """

    result = db.execute(text(query), {"symbol_id": symbol_id}).fetchall()
    return [row[0] for row in result]


def should_calculate_features(db: Session, symbol_id: int) -> bool:
    """Determine if features should be calculated for a symbol"""
    # Check if there are any missing dates
    missing_dates = get_missing_feature_dates(db, symbol_id)
    return len(missing_dates) > 0


def get_eod_data_for_feature_calculation(db: Session, symbol_id: int, lookback_days: int = 60) -> pd.DataFrame:
    """Get EOD data for feature calculation with sufficient lookback"""
    # Get dates needing calculation
    missing_dates = get_missing_feature_dates(db, symbol_id)

    if not missing_dates:
        return pd.DataFrame()  # No missing dates

    # Find earliest missing date and add lookback
    earliest_missing = min(missing_dates)
    from_date = earliest_missing - timedelta(days=lookback_days)

    # Query to get EOD data for calculation
    query = """
        SELECT e.symbol_id, e.date, e.open, e.high, e.low, e.close, e.volume, e.change_percent
        FROM eod_data e
        WHERE e.symbol_id = :symbol_id 
        AND e.date >= :from_date
        ORDER BY e.date
    """

    df = pd.read_sql(text(query), db.bind, params={"symbol_id": symbol_id, "from_date": from_date})
    return df


def save_features(db: Session, features_df: pd.DataFrame) -> Tuple[int, int]:
    """Save calculated features to the database"""
    if features_df.empty:
        return 0, 0

    inserted, skipped = 0, 0

    # Process each row
    for _, row in features_df.iterrows():
        symbol_id = row["symbol_id"]
        feature_date = row["date"]

        # Check if feature already exists
        existing = db.query(FeatureData).filter(FeatureData.symbol_id == symbol_id, FeatureData.date == feature_date).first()

        if existing:
            skipped += 1
            continue

        # Create new feature entry
        feature = FeatureData(symbol_id=symbol_id, date=feature_date, week_day=row.get("week_day"), volatility_squeeze=row.get("volatility_squeeze"), trend_zone_strength=row.get("trend_zone_strength"), range_compression_ratio=row.get("range_compression_ratio"), volume_spike_ratio=row.get("volume_spike_ratio"), body_to_range_ratio=row.get("body_to_range_ratio"), distance_from_ema_5=row.get("distance_from_ema_5"), gap_pct=row.get("gap_pct"), return_3d=row.get("return_3d"), atr_5=row.get("atr_5"), hl_range=row.get("hl_range"), rsi_14=row.get("rsi_14"), close_ema50_gap_pct=row.get("close_ema50_gap_pct"), open_gap_pct=row.get("open_gap_pct"), macd_histogram=row.get("macd_histogram"), atr_14_normalized=row.get("atr_14_normalized"))

        db.add(feature)
        inserted += 1

        # Commit in batches to avoid large transactions
        if inserted % 100 == 0:
            try:
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"Error saving features batch: {e}")

    # Final commit
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error in final commit: {e}")
        return 0, skipped

    return inserted, skipped


def calculate_features_for_symbol(db: Session, symbol_id: int) -> Dict[str, Any]:
    """Calculate features for a single symbol"""
    start_time = time.time()

    try:
        # Check if calculation is needed
        if not should_calculate_features(db, symbol_id):
            symbol = db.query(Symbol).filter(Symbol.id == symbol_id).first()
            logger.info(f"Skipping {symbol.trading_symbol if symbol else symbol_id} — all features up-to-date")
            return {"status": "skipped", "message": "No missing feature dates"}

        # Get symbol info
        symbol = db.query(Symbol).filter(Symbol.id == symbol_id).first()
        if not symbol:
            return {"status": "error", "message": "Symbol not found"}

        # Get EOD data
        eod_df = get_eod_data_for_feature_calculation(db, symbol_id)

        if eod_df.empty:
            return {"status": "skipped", "message": "No EOD data available"}

        # Calculate features
        logger.info(f"Calculating features for {symbol.trading_symbol} with {len(eod_df)} records")
        features_df = calculate_features(eod_df, symbol.trading_symbol)

        if features_df.empty:
            return {"status": "error", "message": "Feature calculation failed"}

        # Get missing dates to filter results
        missing_dates = get_missing_feature_dates(db, symbol_id)
        features_df = features_df[features_df["date"].isin(missing_dates)]

        if features_df.empty:
            return {"status": "skipped", "message": "No new features to save"}

        # Save features
        inserted, skipped = save_features(db, features_df)

        duration = time.time() - start_time
        return {"status": "success", "symbol_id": symbol_id, "trading_symbol": symbol.trading_symbol, "inserted": inserted, "skipped": skipped, "duration": duration}

    except Exception as e:
        logger.error(f"Error calculating features for symbol {symbol_id}: {e}")
        return {"status": "error", "message": str(e)}


def calculate_features_batch(db: Session, symbol_ids: Optional[List[int]] = None, active_only: bool = True) -> Dict[str, Any]:
    """
    Calculate features for a batch of symbols

    Args:
        db: Database session
        symbol_ids: Optional list of symbol IDs to process
        active_only: If True, only process active symbols

    Returns:
        Dictionary with processing statistics
    """
    start_time = time.time()

    # Get symbols to process
    if not symbol_ids:
        query = db.query(Symbol.id)
        if active_only:
            query = query.filter(Symbol.active == True)
        symbol_ids = [s.id for s in query.all()]

    if not symbol_ids:
        logger.warning("No symbols found for feature calculation")
        return {"status": "error", "message": "No symbols found"}

    results = {"total": len(symbol_ids), "successful": 0, "skipped": 0, "errors": 0, "details": {}}

    # Process each symbol
    for i, symbol_id in enumerate(symbol_ids):
        result = calculate_features_for_symbol(db, symbol_id)
        results["details"][symbol_id] = result

        if result["status"] == "success":
            results["successful"] += 1
        elif result["status"] == "skipped":
            results["skipped"] += 1
        else:
            results["errors"] += 1

        # Log progress
        if (i + 1) % 10 == 0 or (i + 1) == len(symbol_ids):
            progress = (i + 1) / len(symbol_ids) * 100
            logger.info(f"Feature calculation progress: {progress:.1f}% - {i+1}/{len(symbol_ids)}")

    # Calculate duration
    duration = time.time() - start_time
    results["duration"] = duration
    logger.info(f"Feature calculation batch completed in {duration:.2f}s - {results['successful']} successful, {results['skipped']} skipped, {results['errors']} errors")

    return results


def get_feature_calculation_status(calculation_id: str) -> Dict[str, Any]:
    """Get the status of a feature calculation batch"""
    if calculation_id not in feature_calculation_status:
        return {"status": "not_found"}

    return feature_calculation_status[calculation_id]


def run_feature_calculation_background(calculation_id: str, symbol_ids: Optional[List[int]] = None, active_only: bool = True, fo_eligible: bool = False):
    """Run feature calculation as a background task with a provided calculation ID"""
    from app.db.session import get_db_session

    db = next(get_db_session())
    feature_calculation_status[calculation_id] = {"status": "running", "started_at": datetime.now().isoformat(), "total": 0, "processed": 0, "successful": 0, "errors": 0, "details": {}}

    # Send initial notification
    asyncio.create_task(notify_feature_calculation_status(calculation_id, "started", {"started_at": feature_calculation_status[calculation_id]["started_at"]}))

    try:
        # Fetch symbol IDs to process
        if not symbol_ids:
            query = db.query(Symbol.id)
            if active_only:
                query = query.filter(Symbol.active)
            if fo_eligible:
                query = query.filter(Symbol.fo_eligible)

            symbol_ids = [s.id for s in query.all()]

        feature_calculation_status[calculation_id]["total"] = len(symbol_ids)

        # Define the worker
        def worker(symbol_id):
            local_db = next(get_db_session())
            try:
                result = calculate_features_for_symbol(local_db, symbol_id)
                return symbol_id, result
            finally:
                local_db.close()

        num_workers = min(32, multiprocessing.cpu_count() * 2)

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {executor.submit(worker, sid): sid for sid in symbol_ids}

            # Track processed count for progress updates
            processed = 0
            for future in as_completed(futures):
                symbol_id, result = future.result()
                feature_calculation_status[calculation_id]["processed"] += 1
                feature_calculation_status[calculation_id]["details"][symbol_id] = result

                processed += 1
                if processed % 5 == 0 or processed == len(symbol_ids):
                    # Send progress update
                    progress = (processed / len(symbol_ids)) * 100
                    asyncio.create_task(notify_feature_calculation_status(calculation_id, "progress", {"processed": processed, "total": len(symbol_ids), "progress": progress}))

                if result["status"] == "success":
                    feature_calculation_status[calculation_id]["successful"] += 1
                elif result["status"] == "error":
                    feature_calculation_status[calculation_id]["errors"] += 1

        feature_calculation_status[calculation_id]["status"] = "completed"
        feature_calculation_status[calculation_id]["completed_at"] = datetime.now().isoformat()

        # Send completion notification
        asyncio.create_task(notify_feature_calculation_status(calculation_id, "completed", {"completed_at": feature_calculation_status[calculation_id]["completed_at"], "successful": feature_calculation_status[calculation_id]["successful"], "errors": feature_calculation_status[calculation_id]["errors"]}))

    except Exception as e:
        feature_calculation_status[calculation_id].update({"status": "error", "completed_at": datetime.now().isoformat(), "error": str(e)})

        asyncio.create_task(notify_feature_calculation_status(calculation_id, "error", {"error": str(e)}))

        logger.error(f"Feature calculation task failed: {e}")
    finally:
        db.close()


async def run_feature_calculation_task(symbol_ids: Optional[List[int]] = None, active_only: bool = True) -> str:
    """Run feature calculation and return the calculation ID"""
    # Generate ID for tracking
    calculation_id = str(int(time.time()))

    # Start the background process
    run_feature_calculation_background(calculation_id, symbol_ids, active_only)

    return calculation_id
