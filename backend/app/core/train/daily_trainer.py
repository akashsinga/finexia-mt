# backend/app/core/train/daily_trainer.py

import os
import pandas as pd
import numpy as np
import joblib
import json
from datetime import datetime
from typing import List, Dict, Tuple, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db_session
from app.db.models.symbol import Symbol
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.db.models.model_performance import ModelPerformance
from app.core.config import get_model_path, get_model_params, LIGHTGBM, RANDOM_FOREST, XGBOOST
from app.core.logger import get_logger
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from app.services.config_service import get_tenant_config
from app.services.symbol_service import get_tenant_watchlist
from app.api.deps import get_current_user
from app.schemas.model import ModelRequest
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = get_logger(__name__)


def get_classifier(classifier_name: str, tenant_id: int = None, db: Session = None):
    """Create classifier with tenant-specific parameters if available."""
    params = get_model_params(classifier_name, db, tenant_id) if tenant_id and db else None

    try:
        if classifier_name == RANDOM_FOREST:
            from sklearn.ensemble import RandomForestClassifier

            return RandomForestClassifier(**(params or {}))

        elif classifier_name == XGBOOST:
            from xgboost import XGBClassifier

            return XGBClassifier(**(params or {}))

        elif classifier_name == LIGHTGBM:
            from lightgbm import LGBMClassifier

            # Remove early_stopping_round if present as it requires eval set
            if params and "early_stopping_round" in params:
                del params["early_stopping_round"]

            return LGBMClassifier(**(params or {}))

        else:
            logger.error(f"Unsupported classifier: {classifier_name}")
            # Default to LightGBM as fallback
            from lightgbm import LGBMClassifier

            return LGBMClassifier()

    except ImportError as e:
        logger.error(f"Library not available: {e}")
        # Fallback to Random Forest which is always available
        from sklearn.ensemble import RandomForestClassifier

        return RandomForestClassifier()


def prepare_data_for_training(symbol_id: int, tenant_id: int = None) -> Tuple[pd.DataFrame, List[str]]:
    """Get and prepare data for model training with tenant context."""
    session = next(get_db_session())

    try:
        # Get feature data for symbol
        query = """
            SELECT * FROM feature_data 
            WHERE symbol_id = :symbol_id
            ORDER BY date
        """
        features_df = pd.read_sql(text(query), session.bind, params={"symbol_id": symbol_id})

        if features_df.empty:
            logger.warning(f"No feature data for symbol {symbol_id}")
            return pd.DataFrame(), []

        # Get price data
        query = """
            SELECT symbol_id, date, close
            FROM eod_data
            WHERE symbol_id = :symbol_id
            ORDER BY date
        """
        closes_df = pd.read_sql(text(query), session.bind, params={"symbol_id": symbol_id})

        if closes_df.empty:
            logger.warning(f"No price data for symbol {symbol_id}")
            return pd.DataFrame(), []

        # Get threshold from tenant config or use default
        threshold_percent = 3.0  # Default
        max_days = 5
        if tenant_id:
            config_threshold = get_tenant_config(session, tenant_id, "STRONG_MOVE_THRESHOLD")
            max_days = get_tenant_config(session, tenant_id, "MAX_DAYS")
            if config_threshold:
                threshold_percent = float(config_threshold)

            if max_days:
                max_days = int(max_days)

        # Process data for training
        return process_training_data(features_df, closes_df, threshold_percent, max_days)

    except Exception as e:
        logger.error(f"Error preparing training data: {e}")
        return pd.DataFrame(), []
    finally:
        session.close()


def process_training_data(features_df: pd.DataFrame, closes_df: pd.DataFrame, threshold_percent: float, max_days: int) -> Tuple[pd.DataFrame, List[str]]:
    """Process data for model training."""
    if features_df.empty or closes_df.empty:
        return pd.DataFrame(), []

    # Ensure date columns are datetime
    features_df["date"] = pd.to_datetime(features_df["date"])
    closes_df["date"] = pd.to_datetime(closes_df["date"])

    # Merge data
    df = pd.merge(features_df, closes_df, on=["symbol_id", "date"])

    # Calculate forward returns (max-day window)
    df["future_max"] = df.groupby("symbol_id")["close"].transform(lambda x: x.rolling(max_days, min_periods=1).max().shift(-max_days))
    df["future_min"] = df.groupby("symbol_id")["close"].transform(lambda x: x.rolling(max_days, min_periods=1).min().shift(-max_days))

    # Calculate percentage moves
    df["up_move_pct"] = (df["future_max"] - df["close"]) / df["close"] * 100
    df["down_move_pct"] = (df["future_min"] - df["close"]) / df["close"] * 100

    # Create target variables
    df["strong_move"] = ((df["up_move_pct"] >= threshold_percent) | (df["down_move_pct"] <= -threshold_percent)).astype(int)
    df["direction"] = (df["up_move_pct"] > abs(df["down_move_pct"])).astype(int)

    # Drop rows with NaN targets
    df = df.dropna(subset=["strong_move", "direction"])

    # Get feature columns (exclude metadata and target columns)
    feature_cols = [col for col in features_df.columns if col not in ["id", "symbol_id", "date", "created_at", "updated_at"]]

    return df, feature_cols


def select_features(X: pd.DataFrame, y: pd.Series, max_features: int = 10) -> List[str]:
    """Select most important features."""
    if X.shape[1] <= max_features:
        return X.columns.tolist()

    try:
        # Handle non-numeric columns and missing values
        X_clean = X.select_dtypes(include=["number"]).fillna(0)

        # Use Random Forest for feature selection
        from sklearn.ensemble import RandomForestClassifier

        model = RandomForestClassifier(n_estimators=50, random_state=42)
        model.fit(X_clean, y)

        # Get feature importance
        importances = pd.Series(model.feature_importances_, index=X_clean.columns)
        return importances.nlargest(max_features).index.tolist()
    except Exception as e:
        logger.warning(f"Feature selection failed: {e}")
        return X.columns.tolist()[:max_features]


def record_model_performance(session: Session, tenant_id: int, symbol_id: int, model_type: str, metrics: Dict[str, float], selected_features: List[str]):
    """Record model performance in database."""
    try:
        # Find or create model entry
        from app.db.models.prediction_model import PredictionModel

        model = session.query(PredictionModel).filter(PredictionModel.tenant_id == tenant_id, PredictionModel.symbol_id == symbol_id, PredictionModel.model_type == model_type, PredictionModel.is_active == True).first()

        if not model:
            # Create new model entry
            model = PredictionModel(tenant_id=tenant_id, symbol_id=symbol_id, name=f"{model_type}_model_{symbol_id}", model_type=model_type, is_active=True, version=datetime.now().strftime("%Y%m%d"), current_accuracy=metrics.get("accuracy", 0))
            session.add(model)
            session.flush()

        # Find or create performance record
        performance = session.query(ModelPerformance).filter(ModelPerformance.tenant_id == tenant_id, ModelPerformance.model_id == model.id, ModelPerformance.evaluation_date == datetime.now().date()).first()

        if not performance:
            performance = ModelPerformance(tenant_id=tenant_id, model_id=model.id, evaluation_date=datetime.now().date())

        # Convert numpy types to Python native types
        def convert_to_python_type(value):
            if value is None:
                return None
            if hasattr(value, "item"):  # Check if it's a numpy type
                return value.item()  # Convert numpy scalar to Python scalar
            return float(value) if isinstance(value, (float, int)) else value

        # Update all available metrics
        performance.accuracy = convert_to_python_type(metrics.get("accuracy", 0))
        performance.precision = convert_to_python_type(metrics.get("precision", 0))
        performance.recall = convert_to_python_type(metrics.get("recall", 0))
        performance.f1_score = convert_to_python_type(metrics.get("f1", 0))
        performance.roc_auc = convert_to_python_type(metrics.get("roc_auc", None))

        # Additional metrics if available
        performance.mse = convert_to_python_type(metrics.get("mse", None))
        performance.rmse = convert_to_python_type(metrics.get("rmse", None))
        performance.mae = convert_to_python_type(metrics.get("mae", None))
        performance.r2 = convert_to_python_type(metrics.get("r2", None))

        # Sample counts
        y_train = metrics.get("y_train", [])
        y_test = metrics.get("y_test", [])
        performance.train_samples = len(y_train) if hasattr(y_train, "__len__") else 0
        performance.test_samples = len(y_test) if hasattr(y_test, "__len__") else 0

        # Training time
        performance.training_time_seconds = convert_to_python_type(metrics.get("training_time", None))

        # Configuration info
        performance.config_hash = metrics.get("config_hash", model_type + "_" + datetime.now().strftime("%Y%m%d"))

        # Convert params dictionary to handle numpy types
        params = metrics.get("params", {})
        python_params = {}
        for k, v in params.items():
            python_params[k] = convert_to_python_type(v)

        performance.hyperparameters = json.dumps({"model_type": model_type, "features": selected_features, "feature_count": len(selected_features), "params": python_params})

        session.add(performance)
        session.commit()
        logger.info(f"Recorded model performance: accuracy {performance.accuracy:.3f}")

    except Exception as e:
        logger.error(f"Failed to record model performance: {e}")
        session.rollback()


def train_model_for_symbol(tenant_id: int, symbol_id: int, db: Session = None) -> Dict[str, Any]:
    """Train models for a symbol with tenant isolation."""
    session = db if db else next(get_db_session())
    start_time = datetime.now()

    try:
        # Verify tenant and symbol
        tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()
        symbol = session.query(Symbol).filter(Symbol.id == symbol_id).first()

        if not tenant or not symbol:
            logger.error(f"Tenant {tenant_id} or symbol {symbol_id} not found")
            return {"status": "error", "message": "Tenant or symbol not found"}

        # Get training data
        df, feature_cols = prepare_data_for_training(symbol_id, tenant_id)

        if df.empty or not feature_cols:
            return {"status": "error", "message": "Insufficient data for training"}

        # Get move prediction targets
        X = df[feature_cols]
        y_move = df["strong_move"]

        # Select best features
        selected_features = select_features(X, y_move)
        X_selected = X[selected_features]

        # Train-test split using time series CV
        train_size = int(len(X_selected) * 0.8)
        X_train = X_selected.iloc[:train_size]
        X_test = X_selected.iloc[train_size:]
        y_train = y_move.iloc[:train_size]
        y_test = y_move.iloc[train_size:]

        # Get model parameters for tenant
        model_type = LIGHTGBM  # Default model type

        if tenant_id:
            config_model_type = get_tenant_config(session, tenant_id, "MODEL_TYPE")
            if config_model_type:
                model_type = config_model_type

        # Train move model
        move_train_start = datetime.now()
        logger.info(f"Training move model for tenant {tenant_id}, symbol {symbol.trading_symbol}")

        move_model = get_classifier(model_type, tenant_id, session)
        move_model.fit(X_train, y_train)

        move_train_duration = (datetime.now() - move_train_start).total_seconds()

        # Calculate metrics
        move_preds = move_model.predict(X_test)
        metrics = {"accuracy": accuracy_score(y_test, move_preds), "precision": precision_score(y_test, move_preds, zero_division=0), "recall": recall_score(y_test, move_preds, zero_division=0), "f1": f1_score(y_test, move_preds, zero_division=0), "y_test": y_test, "y_train": y_train, "training_time": move_train_duration, "params": move_model.get_params(), "config_hash": f"{tenant_id}_{symbol_id}_{model_type}_{datetime.now().strftime('%Y%m%d')}"}

        # Additional metrics if needed
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

        try:
            move_probs = move_model.predict_proba(X_test)[:, 1]
            metrics["mse"] = mean_squared_error(y_test, move_probs)
            metrics["rmse"] = np.sqrt(metrics["mse"])
            metrics["mae"] = mean_absolute_error(y_test, move_probs)
            metrics["r2"] = r2_score(y_test, move_probs)

            from sklearn.metrics import roc_auc_score

            metrics["roc_auc"] = roc_auc_score(y_test, move_probs)
        except Exception as e:
            logger.warning(f"Could not calculate additional metrics: {e}")

        # Save model with metadata
        model_data = {"model": move_model, "selected_features": selected_features, "training_date": datetime.now().date(), "metrics": metrics, "tenant_id": tenant_id}

        model_path = get_model_path(tenant, symbol_id, "move")
        joblib.dump(model_data, model_path)
        logger.info(f"Saved move model for tenant {tenant_id}, symbol {symbol.trading_symbol} - accuracy: {metrics['accuracy']:.3f}")

        # Record performance
        record_model_performance(session, tenant_id, symbol_id, "move", metrics, selected_features)

        # Train direction model if we have enough positive samples
        direction_result = {}
        if df["strong_move"].sum() >= 10:
            # Filter for only strong move samples
            df_strong = df[df["strong_move"] == 1]
            X_dir = df_strong[feature_cols]
            y_dir = df_strong["direction"]

            # Select features
            dir_features = select_features(X_dir, y_dir)
            X_dir_selected = X_dir[dir_features]

            # Train-test split
            if len(X_dir_selected) > 10:
                dir_train_size = int(len(X_dir_selected) * 0.8)
                X_dir_train = X_dir_selected.iloc[:dir_train_size]
                X_dir_test = X_dir_selected.iloc[dir_train_size:]
                y_dir_train = y_dir.iloc[:dir_train_size]
                y_dir_test = y_dir.iloc[dir_train_size:]

                # Train direction model
                dir_train_start = datetime.now()
                dir_model = get_classifier(model_type, tenant_id, session)
                dir_model.fit(X_dir_train, y_dir_train)
                dir_train_duration = (datetime.now() - dir_train_start).total_seconds()

                # Calculate metrics
                dir_preds = dir_model.predict(X_dir_test)
                dir_metrics = {"accuracy": accuracy_score(y_dir_test, dir_preds), "precision": precision_score(y_dir_test, dir_preds, zero_division=0), "recall": recall_score(y_dir_test, dir_preds, zero_division=0), "f1": f1_score(y_dir_test, dir_preds, zero_division=0), "y_test": y_dir_test, "y_train": y_dir_train, "training_time": dir_train_duration, "params": dir_model.get_params(), "config_hash": f"{tenant_id}_{symbol_id}_{model_type}_dir_{datetime.now().strftime('%Y%m%d')}"}

                # Add additional metrics for direction model
                try:
                    dir_probs = dir_model.predict_proba(X_dir_test)[:, 1]
                    dir_metrics["mse"] = mean_squared_error(y_dir_test, dir_probs)
                    dir_metrics["rmse"] = np.sqrt(dir_metrics["mse"])
                    dir_metrics["mae"] = mean_absolute_error(y_dir_test, dir_probs)
                    dir_metrics["r2"] = r2_score(y_dir_test, dir_probs)

                    # Add ROC AUC if possible
                    dir_metrics["roc_auc"] = roc_auc_score(y_dir_test, dir_probs)
                except Exception as e:
                    logger.warning(f"Could not calculate additional metrics for direction model: {e}")

                # Save model
                dir_model_data = {"model": dir_model, "selected_features": dir_features, "training_date": datetime.now().date(), "metrics": dir_metrics, "tenant_id": tenant_id}

                dir_model_path = get_model_path(tenant, symbol_id, "direction")
                joblib.dump(dir_model_data, dir_model_path)
                logger.info(f"Saved direction model for tenant {tenant_id}, symbol {symbol.trading_symbol} - accuracy: {dir_metrics['accuracy']:.3f}")

                # Record performance
                record_model_performance(session, tenant_id, symbol_id, "direction", dir_metrics, dir_features)

                direction_result = {"status": "success", "accuracy": dir_metrics["accuracy"], "precision": dir_metrics["precision"], "recall": dir_metrics["recall"], "f1": dir_metrics["f1"], "feature_count": len(dir_features), "roc_auc": dir_metrics.get("roc_auc"), "mse": dir_metrics.get("mse"), "rmse": dir_metrics.get("rmse"), "mae": dir_metrics.get("mae"), "r2": dir_metrics.get("r2")}
            else:
                direction_result = {"status": "skipped", "reason": "Insufficient samples after split"}
        else:
            direction_result = {"status": "skipped", "reason": "Insufficient strong move samples"}

        # Calculate total duration
        final_duration = (datetime.now() - start_time).total_seconds()

        return {"status": "success", "symbol_id": symbol_id, "move_model": {"accuracy": metrics["accuracy"], "precision": metrics["precision"], "recall": metrics["recall"], "f1": metrics["f1"], "feature_count": len(selected_features)}, "direction_model": direction_result, "duration": final_duration}

    except Exception as e:
        logger.error(f"Error training model for tenant {tenant_id}, symbol {symbol_id}: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        if not db:  # Only close if we created the session
            session.close()


def train_models_for_tenant(tenant_id: int, request: Optional[ModelRequest] = None, current_user: Optional[User] = None) -> Dict[int, Dict[str, Any]]:
    """Train models for all specified symbols for a tenant."""
    session = next(get_db_session())
    results = {}
    symbol_ids = []

    try:
        # Get tenant info
        tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()

        if not tenant:
            logger.error(f"Tenant {tenant_id} not found")
            return results

        # Get symbols for tenant if not provided
        if request and request.symbols:
            symbol_ids = request.symbols
        else:
            # Get symbols based on user/request properties
            if current_user and current_user.is_superadmin:
                query = session.query(Symbol)
                if request and request.is_active:
                    query = query.filter(Symbol.active)
                if request and request.fo_eligible:
                    query = query.filter(Symbol.fo_eligible)
                symbols = query.all()
                symbol_ids = [symbol.id for symbol in symbols]
            else:
                watchlist = get_tenant_watchlist(session, tenant_id, active_only=True, fo_eligible=request.fo_eligible if request else True)
                symbol_ids = [item["symbol_id"] for item in watchlist]

        logger.info(f"Training models for tenant {tenant_id}: {len(symbol_ids)} symbols")

        num_workers = min(32, multiprocessing.cpu_count() * 2)

        def worker(symbol_id):
            local_db = next(get_db_session())
            try:
                return symbol_id, train_model_for_symbol(tenant_id=tenant_id, symbol_id=symbol_id, db=local_db)
            except Exception as e:
                logger.error(f"Training failed for symbol {symbol_id}: {e}")
                return symbol_id, {"status": "error", "message": str(e)}
            finally:
                local_db.close()

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {executor.submit(worker, sid): sid for sid in symbol_ids}
            for future in as_completed(futures):
                sid, result = future.result()
                results[sid] = result

        # Log summary
        success_count = sum(1 for r in results.values() if r.get("status") == "success")
        logger.info(f"Model training for tenant {tenant_id} completed: {success_count}/{len(symbol_ids)} successful")

        return results

    except Exception as e:
        logger.error(f"Error in batch training: {e}")
        return results
    finally:
        session.close()
