# backend/app/core/predict/daily_predictor.py

import os
import joblib
import pandas as pd
import numpy as np
from typing import Dict, Optional, Any, List
from functools import lru_cache
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from app.db.session import get_db_session, SessionLocal
from app.db.models.prediction import Prediction
from app.db.models.symbol import Symbol
from app.db.models.tenant import Tenant
from app.core.config import get_model_path
from app.services.config_service import get_tenant_config
from app.core.logger import get_logger

logger = get_logger(__name__)

# Efficient model cache with tenant isolation
# Key: f"{tenant_id}_{symbol_id}_{model_type}"
model_cache: Dict[str, Dict[str, Any]] = {}
CACHE_SIZE_LIMIT = 100


def load_model_data(tenant_id: int, symbol_id: int, model_type: str) -> Optional[Dict[str, Any]]:
    """Load model data with tenant isolation and caching."""
    cache_key = f"{tenant_id}_{symbol_id}_{model_type}"

    # Return from cache if available
    if cache_key in model_cache:
        return model_cache[cache_key]

    session = next(get_db_session())
    try:
        # Get tenant info
        tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            logger.error(f"Tenant {tenant_id} not found")
            return None

        # Get model path
        model_path = get_model_path(tenant, symbol_id, model_type)
        if not os.path.exists(model_path):
            logger.warning(f"Model not found for tenant {tenant_id}, symbol {symbol_id}")
            return None

        # Load model data (model and metadata)
        model_data = joblib.load(model_path)

        # Standardize format
        if isinstance(model_data, dict) and "model" in model_data:
            result = model_data
        else:
            # Legacy format (just the model)
            result = {"model": model_data, "selected_features": None}

        # Manage cache size
        if len(model_cache) >= CACHE_SIZE_LIMIT:
            # Remove oldest entry
            oldest_key = next(iter(model_cache))
            del model_cache[oldest_key]

        # Add to cache
        model_cache[cache_key] = result
        return result

    except Exception as e:
        logger.error(f"Failed to load model for tenant {tenant_id}, symbol {symbol_id}: {e}")
        return None
    finally:
        session.close()


def prepare_features(features_df: pd.DataFrame, model_data: Dict[str, Any]) -> pd.DataFrame:
    """Prepare features using model-specific feature selection."""
    if features_df.empty:
        return pd.DataFrame()

    # Get selected features if available
    selected_features = model_data.get("selected_features")

    if selected_features:
        # Use only selected features in the right order
        missing_features = [f for f in selected_features if f not in features_df.columns]
        if missing_features:
            logger.warning(f"Missing features: {missing_features}")
            # Create missing columns with zeros
            for feat in missing_features:
                features_df[feat] = 0.0
        return features_df[selected_features]
    else:
        # Use all features excluding non-feature columns
        exclude_cols = ["id", "symbol_id", "date", "created_at", "updated_at"]
        feature_cols = [col for col in features_df.columns if col not in exclude_cols]
        return features_df[feature_cols]


@lru_cache(maxsize=50)
def load_latest_features_for_symbol(symbol_id: int) -> pd.DataFrame:
    """Fetch the latest feature row for the given symbol with caching."""
    session = next(get_db_session())
    try:
        # Use parameterized query for better security
        query = text(
            """
            SELECT * FROM feature_data 
            WHERE symbol_id = :symbol_id
            ORDER BY date DESC
            LIMIT 1
        """
        )
        result = session.execute(query, {"symbol_id": symbol_id})
        row = result.fetchone()

        if not row:
            return pd.DataFrame()

        # Convert result to dictionary
        feature_dict = dict(row._mapping)

        return pd.DataFrame([feature_dict])
    except SQLAlchemyError as e:
        logger.error(f"Database error when loading features for symbol_id {symbol_id}: {e}")
        return pd.DataFrame()
    finally:
        session.close()


def save_prediction(tenant_id: int, symbol_id: int, date, move_confidence: float, direction: Optional[str] = None, direction_confidence: Optional[float] = None) -> bool:
    """Save prediction to database with tenant isolation."""
    session = next(get_db_session())
    try:
        # First delete existing prediction for same symbol, tenant and date
        session.query(Prediction).filter(Prediction.tenant_id == tenant_id, Prediction.symbol_id == symbol_id, Prediction.date == date).delete()

        # Create and add new prediction
        prediction = Prediction(tenant_id=tenant_id, symbol_id=symbol_id, date=date, strong_move_confidence=move_confidence, direction_prediction=direction, direction_confidence=direction_confidence, model_config_hash=f"{tenant_id}_{datetime.now().strftime('%Y%m%d')}")  # Simple tracking
        session.add(prediction)
        session.commit()
        return True
    except SQLAlchemyError as e:
        logger.error(f"Database error saving prediction: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def predict_for_one_symbol(tenant_id: int, symbol_id: int) -> bool:
    """Generate prediction for a single symbol with tenant isolation."""
    session = next(get_db_session())
    start_time = datetime.now()

    try:
        # Verify tenant and symbol exist
        tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()
        symbol = session.query(Symbol).filter(Symbol.id == symbol_id).first()

        if not tenant or not symbol:
            logger.error(f"Tenant {tenant_id} or symbol {symbol_id} not found")
            return False

        # Load latest features
        features_df = load_latest_features_for_symbol(symbol_id)
        if features_df.empty:
            logger.warning(f"No feature data for symbol {symbol_id}")
            return False

        # Load move model
        move_model_data = load_model_data(tenant_id, symbol_id, "move")
        if not move_model_data:
            logger.warning(f"No move model for tenant {tenant_id}, symbol {symbol_id}")
            return False

        # Prepare features
        X = prepare_features(features_df, move_model_data)
        if X.empty:
            logger.warning(f"Failed to prepare features for symbol {symbol_id}")
            return False

        # Make move prediction
        move_model = move_model_data["model"]
        try:
            move_probs = move_model.predict_proba(X)[0]
            strong_move_confidence = float(move_probs[1])
        except Exception as e:
            logger.error(f"Prediction failed for symbol {symbol_id}: {e}")
            return False

        # Direction prediction (only if move confidence is high enough)
        direction_prediction = None
        direction_confidence = None
        
        move_confidence_threshold = 0.5
        
        if tenant_id:
            move_confidence_threshold = get_tenant_config(session, tenant_id, "STRONG_MOVE_CONFIDENCE_THRESHOLD")
            if move_confidence_threshold:
                move_confidence_threshold = float(move_confidence_threshold)

        if strong_move_confidence >= move_confidence_threshold:
            direction_model_data = load_model_data(tenant_id, symbol_id, "direction")
            if direction_model_data:
                try:
                    direction_model = direction_model_data["model"]
                    X_dir = prepare_features(features_df, direction_model_data)

                    dir_probs = direction_model.predict_proba(X_dir)[0]
                    direction_prediction = "UP" if dir_probs[1] > dir_probs[0] else "DOWN"
                    direction_confidence = float(max(dir_probs[0], dir_probs[1]))
                except Exception as e:
                    logger.error(f"Direction prediction failed for symbol {symbol_id}: {e}")

        # Save prediction
        latest_date = features_df.iloc[0]["date"]
        success = save_prediction(tenant_id=tenant_id, symbol_id=symbol_id, date=latest_date, move_confidence=strong_move_confidence, direction=direction_prediction, direction_confidence=direction_confidence)

        if success:
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"Prediction for tenant {tenant_id}, symbol {symbol_id} " f"successful in {duration:.2f}s - Move: {strong_move_confidence:.2f}")
            return True
        else:
            logger.error(f"Failed to save prediction for symbol {symbol_id}")
            return False

    except Exception as e:
        logger.error(f"Error in prediction for symbol {symbol_id}: {e}")
        return False
    finally:
        session.close()


def predict_for_tenant(tenant_id: int, symbols: Optional[List[int]] = None) -> Dict[int, bool]:
    """Generate predictions for all specified symbols for a tenant."""
    session = next(get_db_session())
    results = {}

    try:
        # Get symbols for tenant if not provided
        if not symbols:
            # Get tenant's watchlist symbols
            from app.services.symbol_service import get_tenant_watchlist

            watchlist = get_tenant_watchlist(session, tenant_id, active_only=True)
            symbols = [item["symbol_id"] for item in watchlist]

        logger.info(f"Generating predictions for tenant {tenant_id}, {len(symbols)} symbols")

        # Process each symbol
        for symbol_id in symbols:
            success = predict_for_one_symbol(tenant_id, symbol_id)
            results[symbol_id] = success

        # Log summary
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"Tenant {tenant_id} predictions completed: {success_count}/{len(symbols)} successful")

        return results

    except Exception as e:
        logger.error(f"Error in tenant predictions: {e}")
        return results
    finally:
        session.close()
