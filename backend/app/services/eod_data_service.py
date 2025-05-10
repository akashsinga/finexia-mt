# backend/app/services/eod_data_service.py

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime, timedelta, timezone
import pandas as pd
import time
import os
import requests
import random
import threading
from sqlalchemy import func

from app.db.models.eod_data import EODData
from app.db.models.symbol import Symbol
from app.db.models.config_param import ConfigParam
from app.websockets.connection_manager import connection_manager
from app.core.logger import get_logger
from app.config import settings
from app.services.config_service import get_tenant_config

logger = get_logger(__name__)

INDIA_TZ = timezone(timedelta(hours=5, minutes=30))

# Cache directory
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# In-memory tracking of import status with a lock for thread safety
eod_import_status = {}
eod_status_lock = threading.Lock()

# Rate limiting lock
rate_limit_lock = threading.Semaphore(1)

# API Constants
DHAN_CHARTS_HISTORICAL_URL = "https://api.dhan.co/v2/charts/historical"
DHAN_TODAY_EOD_URL = "https://api.dhan.co/v2/marketfeed/quote"
SAFE_SLEEP_BETWEEN_REQUESTS = 0.5  # Seconds between requests
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2
RETRY_INITIAL_WAIT = 0.5  # seconds

# Default date range
DEFAULT_FROM_DATE = date(2000, 1, 1)


def update_eod_status(task_id: str, updates: Dict[str, Any]):
    """Thread-safe update of EOD import status"""
    with eod_status_lock:
        if task_id not in eod_import_status:
            eod_import_status[task_id] = {"status": "unknown", "started_at": datetime.now().isoformat(), "completed_at": None, "result": None, "error": None, "progress": 0, "processed_symbols": 0, "total_symbols": 0}

        # Update fields
        for key, value in updates.items():
            eod_import_status[task_id][key] = value


async def notify_eod_import_status(task_id: str, status: str, details: Dict[str, Any] = None):
    """Send WebSocket notification about EOD import status"""
    message = {"type": "eod_import_status", "timestamp": datetime.now().isoformat(), "data": {"task_id": task_id, "status": status, **(details or {})}}

    # Broadcast to system topic (for superadmins)
    await connection_manager.broadcast(message, "system")

    # Also broadcast to specific topic for this import task
    await connection_manager.broadcast(message, f"eod_import_{task_id}")


def get_latest_eod_date(db: Session, symbol_id: int) -> Optional[date]:
    """Get the latest EOD date for a specific symbol"""
    result = db.query(EODData.date).filter(EODData.symbol_id == symbol_id).order_by(EODData.date.desc()).first()
    return result[0] if result else None


def is_market_holiday(check_date: date) -> bool:
    """Check if a date is a market holiday"""
    # 2025 Market holidays
    holidays_2025 = [
        date(2025, 1, 1),  # New Year's Day
        date(2025, 1, 26),  # Republic Day
        date(2025, 3, 2),  # Mahashivratri
        date(2025, 3, 17),  # Holi
        date(2025, 4, 14),  # Dr. Ambedkar Jayanti
        date(2025, 4, 18),  # Good Friday
        date(2025, 5, 1),  # Maharashtra Day
        date(2025, 8, 15),  # Independence Day
        date(2025, 9, 2),  # Ganesh Chaturthi
        date(2025, 10, 2),  # Gandhi Jayanti
        date(2025, 10, 23),  # Dussehra
        date(2025, 11, 12),  # Diwali
        date(2025, 11, 14),  # Diwali (Balipratipada)
        date(2025, 12, 25),  # Christmas
    ]

    return check_date in holidays_2025


def is_weekend(check_date: date) -> bool:
    """Check if a date is a weekend (Saturday or Sunday)"""
    return check_date.weekday() >= 5  # 5=Saturday, 6=Sunday


def is_trading_day(check_date: date) -> bool:
    """Check if a date is a valid trading day"""
    return not (is_weekend(check_date) or is_market_holiday(check_date))


def is_market_closed() -> bool:
    """Check if market is closed based on time of day"""
    now = datetime.now(tz=INDIA_TZ)
    # Market closes at 3:30 PM IST
    return now.hour > 15 or (now.hour == 15 and now.minute >= 30)


def get_next_trading_day(current_date: date) -> date:
    """Get the next trading day after the given date"""
    next_date = current_date + timedelta(days=1)
    while not is_trading_day(next_date):
        next_date = next_date + timedelta(days=1)
    return next_date


def get_api_credentials(db: Session, tenant_id: int) -> Dict[str, str]:
    """Get API credentials from Config Params"""
    client_id = get_tenant_config(db, tenant_id, "CLIENT_ID")
    api_key = get_tenant_config(db, tenant_id, "API_KEY")

    if not client_id or not api_key:
        logger.error(f"Missing API credentials for tenant {tenant_id}")

    return {"client_id": client_id or "", "api_key": api_key or ""}


def fetch_eod_from_dhan(db: Session, tenant_id: int, symbol: str, security_id: str, instrument_type: str, exchange_segment: str, from_date: str, to_date: str) -> Optional[Dict]:
    """Fetch EOD data from Dhan API with error handling"""
    # Get API credentials from config
    credentials = get_api_credentials(db, tenant_id)
    if not credentials["client_id"] or not credentials["api_key"]:
        logger.error(f"Missing API credentials for tenant {tenant_id}")
        return None

    payload = {"securityId": str(security_id), "exchangeSegment": exchange_segment, "instrument": instrument_type, "expiryCode": 0, "oi": False, "fromDate": from_date, "toDate": to_date}

    headers = {"Accept": "application/json", "Content-Type": "application/json", "client-id": credentials["client_id"], "access-token": credentials["api_key"]}

    for attempt in range(MAX_RETRIES):
        try:
            # Apply rate limiting
            with rate_limit_lock:
                response = requests.post(DHAN_CHARTS_HISTORICAL_URL, headers=headers, json=payload, timeout=30)
                # Add jitter to sleep time to prevent synchronized retries
                time.sleep(SAFE_SLEEP_BETWEEN_REQUESTS + random.uniform(0.1, 0.5))

            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if hasattr(e, "response") and e.response else "UNKNOWN"

            if status == 429:  # Rate limit
                wait = RETRY_INITIAL_WAIT * (RETRY_BACKOFF_FACTOR**attempt) + random.uniform(0.1, 0.5)
                logger.warning(f"[RETRY] {symbol} hit 429 rate limit. Waiting {wait:.1f}s... (Attempt {attempt+1}/{MAX_RETRIES})")
                time.sleep(wait)
            elif status == 403:  # Auth error
                logger.error(f"[AUTH ERROR] {symbol} hit 403. Check credentials.")
                break
            elif status == 400:  # Bad request
                logger.error(f"[BAD REQUEST] {symbol} hit 400. Likely invalid securityId/segment.")
                break
            else:
                logger.error(f"[HTTP ERROR] {symbol}: {status} - {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_INITIAL_WAIT * (RETRY_BACKOFF_FACTOR**attempt)
                    time.sleep(wait)
                else:
                    break

        except requests.exceptions.ConnectionError as e:
            logger.error(f"[CONNECTION ERROR] {symbol}: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_INITIAL_WAIT * (RETRY_BACKOFF_FACTOR**attempt) * 2
                time.sleep(wait)
            else:
                break

        except requests.exceptions.Timeout as e:
            logger.error(f"[TIMEOUT] {symbol}: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_INITIAL_WAIT * (RETRY_BACKOFF_FACTOR**attempt)
                time.sleep(wait)
            else:
                break

        except Exception as e:
            logger.error(f"[ERROR] Fetch failed for {symbol}: {str(e)}")
            break

    return None


def create_eod_objects(symbol_dict: Dict, data: Dict, existing_dates: set, symbol_prev_close_map: Dict[int, Dict[date, float]]) -> Tuple[List[EODData], int, int]:
    """Create EOD objects from API response with data validation"""
    if not data or "timestamp" not in data:
        return [], 0, 0

    candles = []
    skipped_dupe = 0
    skipped_invalid = 0

    try:
        ts_list = data.get("timestamp", [])
        open_list = data.get("open", [])
        high_list = data.get("high", [])
        low_list = data.get("low", [])
        close_list = data.get("close", [])
        volume_list = data.get("volume", [])

        # Validate lengths match
        if not (len(ts_list) == len(open_list) == len(high_list) == len(low_list) == len(close_list) == len(volume_list)):
            logger.warning(f"[WARNING] Data length mismatch for {symbol_dict['trading_symbol']}")
            return [], 0, 0

        # Track new seen dates to avoid duplicates within this batch
        seen_dates = set()

        # Sort by timestamp ascending for correct prev_close calculation
        sorted_indices = sorted(range(len(ts_list)), key=lambda i: ts_list[i])

        # Initialize prev_close lookup dict for this symbol if needed
        symbol_id = symbol_dict["id"]
        if symbol_id not in symbol_prev_close_map:
            symbol_prev_close_map[symbol_id] = {}

        # Track previous close for change percent calculation
        prev_close = None

        for idx in sorted_indices:
            ts = ts_list[idx]
            # Convert timestamp to date
            dt = datetime.fromtimestamp(ts).date()

            # Skip duplicates (both existing in DB and within this batch)
            if dt in existing_dates or dt in seen_dates:
                skipped_dupe += 1
                continue

            seen_dates.add(dt)

            # Data validation
            try:
                open_val = float(open_list[idx])
                high_val = float(high_list[idx])
                low_val = float(low_list[idx])
                close_val = float(close_list[idx])
                volume_val = int(volume_list[idx])

                # Skip invalid data
                if open_val <= 0 or high_val <= 0 or low_val <= 0 or close_val <= 0 or high_val < low_val or high_val < open_val or high_val < close_val or low_val > open_val or low_val > close_val:
                    logger.warning(f"[WARNING] Invalid price data for {symbol_dict['trading_symbol']} on {dt}")
                    skipped_invalid += 1
                    continue

                # Calculate change percent using the previous close
                change_percent = None
                if prev_close is not None and prev_close > 0:
                    change_percent = ((close_val - prev_close) / prev_close) * 100

                # Ensure change_percent is never NULL
                if change_percent is None:
                    change_percent = 0.0

                # Create EOD object
                candles.append(EODData(symbol_id=symbol_id, date=dt, open=open_val, high=high_val, low=low_val, close=close_val, volume=volume_val, change_percent=change_percent))

                # Save close for next day's calculation
                prev_close = close_val
                symbol_prev_close_map[symbol_id][dt] = close_val

            except (ValueError, TypeError) as e:
                logger.warning(f"[WARNING] Invalid data format for {symbol_dict['trading_symbol']} on {dt}: {e}")
                skipped_invalid += 1

    except Exception as e:
        logger.error(f"[WARNING] Failed parsing {symbol_dict['trading_symbol']}: {str(e)}")

    return candles, skipped_dupe, skipped_invalid


def fetch_existing_eod_dates(db: Session, symbol_id: int) -> set:
    """Fetch all existing EOD dates for a symbol to avoid duplicates"""
    dates = db.query(EODData.date).filter(EODData.symbol_id == symbol_id).all()
    return {d[0] for d in dates}


def get_prev_close_map(db: Session) -> Dict[int, Dict[date, float]]:
    """Get previous close prices for all symbols"""
    prev_close_map = {}

    # Query all EOD data
    eod_records = db.query(EODData.symbol_id, EODData.date, EODData.close).all()

    # Build lookup map
    for symbol_id, dt, close in eod_records:
        if symbol_id not in prev_close_map:
            prev_close_map[symbol_id] = {}

        prev_close_map[symbol_id][dt] = close

    return prev_close_map


def bulk_insert_eod_data(db: Session, candles: List[EODData]) -> int:
    """Bulk insert EOD data with error handling"""
    try:
        if not candles:
            return 0

        # Ensure no NULL change_percent values
        for candle in candles:
            if candle.change_percent is None:
                candle.change_percent = 0.0

        db.bulk_save_objects(candles)
        db.commit()
        return len(candles)
    except Exception as e:
        db.rollback()
        logger.error(f"Bulk insert failed: {str(e)}")

        # Try individual inserts if bulk fails
        inserted = 0
        for candle in candles:
            try:
                # Make sure change_percent is not NULL
                if candle.change_percent is None:
                    candle.change_percent = 0.0

                db.add(candle)
                db.commit()
                inserted += 1
            except Exception as inner_e:
                db.rollback()
                logger.error(f"Individual insert failed for {candle.date}: {str(inner_e)}")

        return inserted


def import_eod_data(db: Session, symbol_id: int, data: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Import EOD data for a specific symbol

    Returns:
        Tuple of (inserted_count, updated_count)
    """
    inserted, updated = 0, 0

    for item in data:
        # Check if record already exists
        existing = db.query(EODData).filter(EODData.symbol_id == symbol_id, EODData.date == item["date"]).first()

        # Calculate change percent - this will already be in the item
        change_percent = item.get("change_percent")
        # Ensure change_percent is never NULL
        if change_percent is None:
            change_percent = 0.0

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
            new_record = EODData(symbol_id=symbol_id, date=item["date"], open=item["open"], high=item["high"], low=item["low"], close=item["close"], volume=item["volume"], change_percent=change_percent)
            db.add(new_record)
            inserted += 1

    db.commit()
    return inserted, updated


def import_eod_data_from_dataframe(db: Session, symbol_id: int, df: pd.DataFrame) -> Tuple[int, int]:
    """Import EOD data from a pandas DataFrame"""
    # Convert DataFrame to list of dicts
    records = df.to_dict("records")

    # Import the records
    return import_eod_data(db, symbol_id, records)


def get_eod_data(db: Session, symbol_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None, limit: int = None) -> List[EODData]:
    """Get EOD data for a specific symbol with date range filtering"""
    query = db.query(EODData).filter(EODData.symbol_id == symbol_id)

    if start_date:
        query = query.filter(EODData.date >= start_date)

    if end_date:
        query = query.filter(EODData.date <= end_date)

    # Order by date descending (newest first)
    query = query.order_by(EODData.date.asc())

    # Apply limit
    return query.limit(limit).all()


def fetch_today_eod_data(db: Session, tenant_id: int, symbol_dict: Dict, today: date, prev_close_map: Dict[int, Dict[date, float]]) -> Optional[EODData]:
    """Fetch today's EOD data from DHAN API"""
    # Get API credentials from config
    credentials = get_api_credentials(db, tenant_id)
    if not credentials["client_id"] or not credentials["api_key"]:
        logger.error(f"Missing API credentials for tenant {tenant_id}")
        return None

    # Only proceed if market is closed
    if not is_market_closed():
        logger.info(f"Market still open, skipping today's data fetch for {symbol_dict['trading_symbol']}")
        return None

    segment = symbol_dict["segment"].split("_")[0]  # Extract NSE from NSE_EQ

    payload = {segment: [int(symbol_dict["security_id"])]}

    headers = {"Accept": "application/json", "Content-Type": "application/json", "client-id": credentials["client_id"], "access-token": credentials["api_key"]}

    for attempt in range(MAX_RETRIES):
        try:
            # Apply rate limiting
            with rate_limit_lock:
                response = requests.post(DHAN_TODAY_EOD_URL, headers=headers, json=payload, timeout=30)
                # Add jitter to sleep time to prevent synchronized retries
                time.sleep(SAFE_SLEEP_BETWEEN_REQUESTS + random.uniform(0.1, 0.5))

            response.raise_for_status()
            result = response.json()

            # Check for API error responses
            if result.get("status") != "success":
                error_msg = result.get("message", "Unknown API error")
                logger.error(f"[API ERROR] {symbol_dict['trading_symbol']}: {error_msg}")
                return None

            # Extract data
            data = result.get("data", {}).get(segment, {})
            if not data:
                logger.warning(f"No data returned for {symbol_dict['trading_symbol']}")
                return None

            # Process quote data
            sec_id_str = str(symbol_dict["security_id"])
            if sec_id_str not in data:
                logger.warning(f"Security ID {sec_id_str} not found in response for {symbol_dict['trading_symbol']}")
                return None

            quote = data[sec_id_str]
            ohlc = quote.get("ohlc", {})

            if not all(k in ohlc for k in ["open", "high", "low", "close"]):
                logger.warning(f"Missing OHLC data for {symbol_dict['trading_symbol']}")
                return None

            # Extract values
            open_val = float(ohlc.get("open", 0))
            high_val = float(ohlc.get("high", 0))
            low_val = float(ohlc.get("low", 0))
            close_val = float(ohlc.get("close", 0))
            volume_val = int(quote.get("volume", 0))

            # Skip invalid data
            if open_val <= 0 or high_val <= 0 or low_val <= 0 or close_val <= 0 or high_val < low_val or high_val < open_val or high_val < close_val or low_val > open_val or low_val > close_val:
                logger.warning(f"[WARNING] Invalid price data for {symbol_dict['trading_symbol']} on {today}")
                return None

            # Calculate change percent
            change_percent = None
            symbol_id = symbol_dict["id"]

            # Find the previous trading day
            prev_day = today - timedelta(days=1)
            while not is_trading_day(prev_day):
                prev_day = prev_day - timedelta(days=1)

            # Check if we have the previous close
            if symbol_id in prev_close_map and prev_day in prev_close_map[symbol_id]:
                prev_close = prev_close_map[symbol_id][prev_day]
                if prev_close > 0:
                    change_percent = ((close_val - prev_close) / prev_close) * 100

            # Ensure change_percent is never NULL
            if change_percent is None:
                change_percent = 0.0

            # Create EOD object
            return EODData(symbol_id=symbol_id, date=today, open=open_val, high=high_val, low=low_val, close=close_val, volume=volume_val, change_percent=change_percent)

        except Exception as e:
            logger.error(f"[ERROR] Failed to fetch today's data for {symbol_dict['trading_symbol']}: {str(e)}")

            if attempt < MAX_RETRIES - 1:
                wait = RETRY_INITIAL_WAIT * (RETRY_BACKOFF_FACTOR**attempt)
                time.sleep(wait)

    return None


async def fetch_and_insert_one_symbol(db: Session, tenant_id: int, symbol_dict: Dict, today: date, prev_close_map: Dict[int, Dict[date, float]], task_id: str) -> str:
    """Fetch and insert EOD data for one symbol with optimized database operations"""
    start_time = time.time()

    try:
        symbol = symbol_dict["trading_symbol"]
        symbol_id = symbol_dict["id"]

        # Fetch existing dates to avoid duplicates
        existing_dates = fetch_existing_eod_dates(db, symbol_id)

        # Logic A: Check if we have any data at all
        if not existing_dates:
            # No historical data, fetch from default date
            from_date = DEFAULT_FROM_DATE
            to_date = today - timedelta(days=1)  # Exclude today when fetching historical data

            # Only fetch historical data if today is not a holiday or weekend
            if not is_trading_day(today):
                # Find the last trading day before today
                to_date = today - timedelta(days=1)
                while not is_trading_day(to_date):
                    to_date = to_date - timedelta(days=1)

            logger.info(f"No historical data for {symbol}, fetching from {from_date} to {to_date}")

            # Fetch historical data
            data = fetch_eod_from_dhan(db=db, tenant_id=tenant_id, symbol=symbol, security_id=symbol_dict["security_id"], instrument_type=symbol_dict["instrument_type"], exchange_segment=symbol_dict["segment"], from_date=from_date.strftime("%Y-%m-%d"), to_date=to_date.strftime("%Y-%m-%d"))

            if data is None:
                return f"[FAIL] {symbol} - historical fetch failed"

            if "timestamp" not in data or not data["timestamp"]:
                return f"[SKIP] {symbol} - no historical data"

            # Process data
            candles, skipped_dupe, skipped_invalid = create_eod_objects(symbol_dict, data, existing_dates, prev_close_map)

            if candles:
                # Bulk insert
                inserted = bulk_insert_eod_data(db, candles)
                logger.info(f"Inserted {inserted} historical records for {symbol}")

                # Update existing dates for next steps
                existing_dates.update({c.date for c in candles})

        # Logic B: Check for gaps between last available date and today
        last_eod_date = get_latest_eod_date(db, symbol_id)
        if last_eod_date:
            # Find the next trading day after last_eod_date
            next_date = get_next_trading_day(last_eod_date)

            # Check if there's a gap, but exclude today
            yesterday = today - timedelta(days=1)

            if next_date <= yesterday:
                logger.info(f"Gap detected for {symbol}: {last_eod_date} to {yesterday}")

                # Fetch gap data - only up to yesterday
                data = fetch_eod_from_dhan(db=db, tenant_id=tenant_id, symbol=symbol, security_id=symbol_dict["security_id"], instrument_type=symbol_dict["instrument_type"], exchange_segment=symbol_dict["segment"], from_date=next_date.strftime("%Y-%m-%d"), to_date=yesterday.strftime("%Y-%m-%d"))

                if data and "timestamp" in data and data["timestamp"]:
                    # Process gap data
                    candles, skipped_dupe, skipped_invalid = create_eod_objects(symbol_dict, data, existing_dates, prev_close_map)

                    if candles:
                        # Bulk insert
                        inserted = bulk_insert_eod_data(db, candles)
                        logger.info(f"Inserted {inserted} gap records for {symbol}")

                        # Update existing dates for next step
                        existing_dates.update({c.date for c in candles})

        # Logic C: Fetch today's data separately if it's a trading day and not already in DB
        if is_trading_day(today) and today not in existing_dates:
            logger.info(f"Fetching today's data for {symbol}")

            # Fetch today's EOD data using market quote API
            today_data = fetch_today_eod_data(db, tenant_id, symbol_dict, today, prev_close_map)

            if today_data:
                # Make sure change_percent is not NULL
                if today_data.change_percent is None:
                    today_data.change_percent = 0.0

                # Insert today's data
                db.add(today_data)
                db.commit()
                logger.info(f"Inserted today's data for {symbol}")

                # Store today's close for future calculations
                if symbol_id not in prev_close_map:
                    prev_close_map[symbol_id] = {}
                prev_close_map[symbol_id][today] = today_data.close

        elapsed = time.time() - start_time
        return f"[OK] {symbol} - processed in {elapsed:.2f}s"

    except Exception as e:
        db.rollback()
        return f"[ERROR] {symbol_dict['trading_symbol']} failed: {str(e)}"


async def run_eod_import_task(task_id: str, tenant_id: int, force_download: bool = False):
    """Background task for EOD data import that updates status tracking and sends WebSocket notifications"""
    from app.db.session import get_db_session

    try:
        # Update status to started
        update_eod_status(task_id, {"status": "started", "started_at": datetime.now(tz=INDIA_TZ).isoformat(), "progress": 0, "processed_symbols": 0})

        # Send initial notification
        await notify_eod_import_status(task_id, "started", {"started_at": eod_import_status[task_id]["started_at"], "message": "EOD data import started"})

        # Get DB session
        session = next(get_db_session())

        # Get all active symbols
        symbols = session.query(Symbol).filter(Symbol.active == True).all()
        total_symbols = len(symbols)
        update_eod_status(task_id, {"total_symbols": total_symbols})

        # Send start notification with total count
        await notify_eod_import_status(task_id, "started", {"message": f"EOD data import started for {total_symbols} symbols", "total_symbols": total_symbols})

        # Get today's date
        today = datetime.now(tz=INDIA_TZ).date()

        # Prepare symbol dicts
        symbol_dicts = [
            {
                "id": s.id,
                "security_id": str(s.security_id),
                "trading_symbol": s.trading_symbol,
                "exchange": s.exchange,
                "instrument_type": s.instrument_type,
                "segment": s.segment,
            }
            for s in symbols
        ]

        # Get previous close data
        prev_close_map = get_prev_close_map(session)

        session.close()

        # Process symbols sequentially (could be made parallel)
        completed, failed = 0, 0
        for i, sym_dict in enumerate(symbol_dicts):
            # Get a new session for each symbol
            session = next(get_db_session())

            result = await fetch_and_insert_one_symbol(db=session, tenant_id=tenant_id, symbol_dict=sym_dict, today=today, prev_close_map=prev_close_map, task_id=task_id)

            session.close()

            logger.info(result)

            if result.startswith("[OK]"):
                completed += 1
            elif result.startswith("[FAIL]") or result.startswith("[ERROR]"):
                failed += 1

            # Update progress
            progress = (i + 1) / total_symbols * 100
            update_eod_status(task_id, {"progress": progress, "processed_symbols": i + 1})

            # Send progress update every 5% or 10 symbols
            if (i + 1) % 10 == 0 or progress % 5 < 1:
                await notify_eod_import_status(task_id, "progress", {"progress": progress, "processed_symbols": i + 1, "successful_symbols": completed, "failed_symbols": failed, "message": f"Processed {i + 1} of {total_symbols} symbols ({progress:.1f}%)"})

        # Update status with result
        update_eod_status(task_id, {"status": "completed", "completed_at": datetime.now().isoformat(), "progress": 100, "result": {"successful": completed, "failed": failed, "total": total_symbols}})

        # Send final notification
        await notify_eod_import_status(task_id, "completed", {"completed_at": eod_import_status[task_id]["completed_at"], "result": eod_import_status[task_id]["result"], "message": f"EOD data import completed: {completed} successful, {failed} failed"})

    except Exception as e:
        # Update status with error
        error_msg = str(e)
        update_eod_status(task_id, {"status": "failed", "completed_at": datetime.now().isoformat(), "error": error_msg})

        # Send error notification
        await notify_eod_import_status(task_id, "failed", {"completed_at": eod_import_status[task_id]["completed_at"], "error": error_msg, "message": f"EOD data import failed: {error_msg}"})


def get_import_status(task_id: str) -> Dict[str, Any]:
    """Get the current status of an EOD import task"""
    with eod_status_lock:
        if task_id not in eod_import_status:
            return {"status": "not_found", "message": "Import task not found"}

        # Return a copy to avoid race conditions
        return dict(eod_import_status[task_id])


def check_data_availability(db: Session, from_date: date = None, to_date: date = None) -> Dict[str, Any]:
    """
    Check data availability in the specified period

    Args:
        db: Database session
        from_date: Optional from date
        to_date: Optional to date

    Returns:
        Dictionary with availability statistics
    """
    if not to_date:
        to_date = datetime.now().date()

    if not from_date:
        from_date = to_date - timedelta(days=30)

    trading_days = []
    current_date = from_date
    while current_date <= to_date:
        if is_trading_day(current_date):
            trading_days.append(current_date)
        current_date += timedelta(days=1)

    # Get active symbols
    active_symbol_count = db.query(func.count(Symbol.id)).filter(Symbol.active == True).scalar()

    # Get data points per day
    data_points = []
    for day in trading_days:
        count = db.query(func.count(EODData.id)).filter(EODData.date == day).scalar()
        coverage = count / active_symbol_count if active_symbol_count > 0 else 0
        data_points.append({"date": day.isoformat(), "count": count, "coverage": coverage})

    # Get overall statistics
    total_data_points = db.query(func.count(EODData.id)).filter(EODData.date >= from_date, EODData.date <= to_date).scalar()

    ideal_data_points = len(trading_days) * active_symbol_count
    overall_coverage = total_data_points / ideal_data_points if ideal_data_points > 0 else 0

    # Get symbols with missing data
    symbols_with_missing_data = []

    # This can be inefficient for large datasets, so limit to recent days
    recent_trading_day = trading_days[-1] if trading_days else to_date

    # Check for symbols missing today's data
    if is_trading_day(recent_trading_day) and is_market_closed():
        symbols_with_recent_data = db.query(EODData.symbol_id).filter(EODData.date == recent_trading_day).distinct().all()

        symbols_with_recent_data_ids = {s[0] for s in symbols_with_recent_data}

        missing_symbols = db.query(Symbol).filter(Symbol.active == True, ~Symbol.id.in_(symbols_with_recent_data_ids)).all()

        for symbol in missing_symbols:
            symbols_with_missing_data.append({"id": symbol.id, "trading_symbol": symbol.trading_symbol, "exchange": symbol.exchange})

    return {"from_date": from_date.isoformat(), "to_date": to_date.isoformat(), "trading_days": len(trading_days), "active_symbols": active_symbol_count, "total_data_points": total_data_points, "ideal_data_points": ideal_data_points, "overall_coverage": overall_coverage, "data_points_by_day": data_points, "symbols_with_missing_data": symbols_with_missing_data}
