# backend/app/scripts/import_symbol_master.py
import pandas as pd
import requests
import hashlib
import json
import os
from io import StringIO
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models.symbol import Symbol
from app.core.logger import get_logger

logger = get_logger(__name__)

# Constants
DHAN_SCRIP_MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_FILE = os.path.join(CACHE_DIR, "scrip_master_cache.csv")
CHECKSUM_FILE = os.path.join(CACHE_DIR, "scrip_master_checksum.txt")
CHANGES_LOG_DIR = os.path.join(CACHE_DIR, "symbol_changes")
os.makedirs(CHANGES_LOG_DIR, exist_ok=True)


def calculate_checksum(data: str) -> str:
    """Calculate MD5 checksum of data."""
    return hashlib.md5(data.encode("utf-8")).hexdigest()


def fetch_symbol_data(use_cache: bool = True) -> pd.DataFrame:
    """
    Fetch symbol data from the source.

    Args:
        use_cache: Whether to use cached data if available

    Returns:
        DataFrame with symbol data
    """
    try:
        # Download CSV
        logger.info(f"Downloading master data from {DHAN_SCRIP_MASTER_URL}")
        response = requests.get(DHAN_SCRIP_MASTER_URL, timeout=60)
        response.raise_for_status()

        csv_text = response.text
        new_checksum = calculate_checksum(csv_text)

        # Check if we have a cached version
        if use_cache and os.path.exists(CACHE_FILE) and os.path.exists(CHECKSUM_FILE):
            with open(CHECKSUM_FILE, "r") as f:
                old_checksum = f.read().strip()

            if old_checksum == new_checksum:
                logger.info("Using cached scrip master file (unchanged)")
                return pd.read_csv(CACHE_FILE, low_memory=False)

        # Parse the CSV
        df = pd.read_csv(StringIO(csv_text), low_memory=False)

        # Validate data
        if df.empty:
            raise Exception("Downloaded CSV is empty")

        required_columns = ["SEM_SMST_SECURITY_ID", "SEM_TRADING_SYMBOL", "SEM_EXM_EXCH_ID", "SM_SYMBOL_NAME", "SEM_SEGMENT", "SEM_EXCH_INSTRUMENT_TYPE"]

        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise Exception(f"CSV missing required columns: {', '.join(missing)}")

        # Cache the file and checksum
        os.makedirs(CACHE_DIR, exist_ok=True)
        df.to_csv(CACHE_FILE, index=False)
        with open(CHECKSUM_FILE, "w") as f:
            f.write(new_checksum)

        logger.info("Symbol data downloaded and parsed successfully")
        return df

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error fetching symbol data: {e}")
        if use_cache and os.path.exists(CACHE_FILE):
            logger.info("Using cached data due to network error")
            return pd.read_csv(CACHE_FILE, low_memory=False)
        raise
    except Exception as e:
        logger.error(f"Error processing symbol data: {e}")
        if use_cache and os.path.exists(CACHE_FILE):
            logger.info("Using cached data due to processing error")
            return pd.read_csv(CACHE_FILE, low_memory=False)
        raise


def prepare_symbol_data(df_full: pd.DataFrame) -> pd.DataFrame:
    """
    Filter and prepare symbol data for import.

    Args:
        df_full: Raw data from source

    Returns:
        Processed DataFrame ready for import
    """
    # Identify derivatives symbols for F&O eligibility
    fo_symbols = df_full[(df_full["SEM_SEGMENT"] == "D") & (df_full["SEM_EXCH_INSTRUMENT_TYPE"].isin(["FUTSTK", "OPTSTK"]))]["SEM_TRADING_SYMBOL"].unique().tolist()

    # Filter NSE EQ stocks
    df = df_full[(df_full["SEM_SEGMENT"] == "E") & (df_full["SEM_EXCH_INSTRUMENT_TYPE"] == "ES") & (df_full["SEM_EXM_EXCH_ID"] == "NSE")].copy()

    # Add F&O eligibility flag
    df["fo_eligible"] = df["SEM_TRADING_SYMBOL"].apply(lambda x: any(derivative.startswith(x + "-") for derivative in fo_symbols))

    logger.info(f"Prepared {len(df)} NSE equity symbols for import")
    return df


def process_symbols(db: Session, df: pd.DataFrame) -> Tuple[int, int, int, List[Dict]]:
    """
    Process symbols data and update the database.

    Args:
        db: Database session
        df: Prepared symbol data

    Returns:
        Tuple of (added, updated, deactivated, changes)
    """
    # Get existing symbols
    existing_symbols = {s.trading_symbol: s for s in db.query(Symbol).all()}

    added, updated, unchanged = 0, 0, 0
    changes = []

    # Process symbols
    for _, row in df.iterrows():
        trading_symbol = row["SEM_TRADING_SYMBOL"]
        security_id = str(row.get("SEM_SMST_SECURITY_ID", "")).strip()
        exchange = row.get("SEM_EXM_EXCH_ID", "")
        name = row.get("SM_SYMBOL_NAME", "")
        instrument_type = "EQUITY"
        segment = f"{exchange}_EQ"
        lot_size = int(row["SEM_LOT_UNITS"]) if pd.notnull(row["SEM_LOT_UNITS"]) else None
        fo_eligible = row.get("fo_eligible", False)

        if trading_symbol in existing_symbols:
            # Check for changes
            symbol = existing_symbols[trading_symbol]
            symbol_changes = {}
            changes_detected = False

            if symbol.security_id != security_id:
                symbol_changes["security_id"] = {"old": symbol.security_id, "new": security_id}
                symbol.security_id = security_id
                changes_detected = True

            if symbol.name != name:
                symbol_changes["name"] = {"old": symbol.name, "new": name}
                symbol.name = name
                changes_detected = True

            if symbol.segment != segment:
                symbol_changes["segment"] = {"old": symbol.segment, "new": segment}
                symbol.segment = segment
                changes_detected = True

            if symbol.lot_size != lot_size:
                symbol_changes["lot_size"] = {"old": symbol.lot_size, "new": lot_size}
                symbol.lot_size = lot_size
                changes_detected = True

            if symbol.fo_eligible != fo_eligible:
                symbol_changes["fo_eligible"] = {"old": symbol.fo_eligible, "new": fo_eligible}
                symbol.fo_eligible = fo_eligible
                changes_detected = True

            if not symbol.active:
                symbol_changes["active"] = {"old": symbol.active, "new": True}
                symbol.active = True
                changes_detected = True

            if changes_detected:
                updated += 1
                changes.append({"symbol": trading_symbol, "changes": symbol_changes})
            else:
                unchanged += 1
        else:
            # Add new symbol
            symbol = Symbol(
                security_id=security_id,
                exchange=exchange,
                trading_symbol=trading_symbol,
                name=name,
                instrument_type=instrument_type,
                segment=segment,
                lot_size=lot_size,
                active=True,
                fo_eligible=fo_eligible,
            )
            db.add(symbol)
            added += 1
            changes.append({"symbol": trading_symbol, "action": "added"})

    # Mark missing symbols as inactive
    current_symbols = set(df["SEM_TRADING_SYMBOL"].unique())
    deactivated = 0
    for symbol in existing_symbols.values():
        if symbol.trading_symbol not in current_symbols and symbol.active:
            symbol.active = False
            deactivated += 1
            changes.append({"symbol": symbol.trading_symbol, "action": "deactivated"})

    # Save changes
    db.commit()

    return added, updated, deactivated, changes


def save_change_log(changes: List[Dict]) -> str:
    """
    Save changes to a log file.

    Args:
        changes: List of changes to save

    Returns:
        Path to the log file
    """
    if not changes:
        return None

    change_log_file = os.path.join(CHANGES_LOG_DIR, f"symbol_changes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(change_log_file, "w") as f:
        json.dump(changes, f, indent=2)

    return change_log_file


def import_symbols(force_download: bool = False) -> Dict[str, Any]:
    """
    Main function to import symbols.

    Args:
        force_download: Whether to force download instead of using cache

    Returns:
        Dictionary with import results
    """
    session = SessionLocal()
    start_time = datetime.now()
    result = {"success": False, "error": None, "stats": {}}

    try:
        # Fetch and prepare data
        df_full = fetch_symbol_data(use_cache=not force_download)
        df = prepare_symbol_data(df_full)

        # Process symbols
        added, updated, deactivated, changes = process_symbols(session, df)

        # Save change log
        log_file = save_change_log(changes)
        if log_file:
            logger.info(f"Change log saved to {log_file}")

        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()

        # Prepare result
        result["success"] = True
        result["stats"] = {"added": added, "updated": updated, "unchanged": len(df) - added - updated, "deactivated": deactivated, "total_processed": len(df), "duration_seconds": duration, "change_log": log_file}

        logger.info(f"Symbol import completed in {duration:.1f}s - Added: {added}, " f"Updated: {updated}, Deactivated: {deactivated}")

    except Exception as e:
        session.rollback()
        error_msg = str(e)
        logger.error(f"Symbol import failed: {error_msg}")
        result["error"] = error_msg
    finally:
        session.close()

    return result


if __name__ == "__main__":
    # When run as a script, execute the import
    result = import_symbols()
    if not result["success"]:
        exit(1)
