# app/core/config.py

import os
from typing import Dict, Any, Optional
from pathlib import Path
from sqlalchemy.orm import Session

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CORE_DIR = BASE_DIR / "core"
MODELS_DIR = BASE_DIR / "models"

# Ensure directories exist
os.makedirs(MODELS_DIR, exist_ok=True)

# Model types
LIGHTGBM = "lightgbm"
XGBOOST = "xgboost"
RANDOM_FOREST = "random_forest"

# Feature importance
MIN_FEATURE_IMPORTANCE = 0.01
MAX_FEATURES_TO_USE = 20

# Time-series cross-validation
CV_N_SPLITS = 3
CV_TEST_SIZE = 0.2

# Default hyperparameters (fallbacks if not in config table)
DEFAULT_PARAMS = {LIGHTGBM: {"n_estimators": 100, "learning_rate": 0.1, "max_depth": 6, "num_leaves": 31, "min_child_weight": 3, "colsample_bytree": 0.8, "subsample": 0.8, "random_state": 42, "n_jobs": -1, "importance_type": "gain"}, XGBOOST: {"n_estimators": 100, "learning_rate": 0.1, "max_depth": 6, "gamma": 0.1, "min_child_weight": 3, "colsample_bytree": 0.8, "subsample": 0.8, "random_state": 42, "n_jobs": -1, "importance_type": "gain"}, RANDOM_FOREST: {"n_estimators": 100, "max_depth": 8, "min_samples_split": 5, "min_samples_leaf": 2, "max_features": "sqrt", "random_state": 42, "class_weight": "balanced", "n_jobs": -1}}


def get_tenant_model_dir(tenant) -> Path:
    """
    Get the model directory for a tenant.

    Args:
        tenant: The tenant object (with id and name)

    Returns:
        Path object for the tenant's model directory
    """
    # Create directory with tenant name_id for better identification
    dir_name = f"{tenant.name}_{tenant.id}"
    # Replace any problematic characters in the directory name
    dir_name = "".join(c if c.isalnum() or c in ["-", "_"] else "_" for c in dir_name)

    tenant_dir = MODELS_DIR / dir_name
    os.makedirs(tenant_dir, exist_ok=True)
    return tenant_dir


def get_model_path(tenant, symbol_id: int, model_type: str) -> Path:
    """
    Get the path for a model file. We only keep one active model per symbol.

    Args:
        tenant: The tenant object
        symbol_id: The symbol ID
        model_type: Model type (move or direction)

    Returns:
        Path object for the model file
    """
    tenant_dir = get_tenant_model_dir(tenant)

    # Simple filename format for single active model
    filename = f"{symbol_id}_{model_type}_model.pkl"

    return tenant_dir / filename


def get_model_config(db: Session, tenant_id: int) -> Dict[str, Any]:
    """
    Get model configuration parameters from the ConfigParams table

    Args:
        db: Database session
        tenant_id: Tenant ID

    Returns:
        Dictionary of configuration parameters
    """
    from app.services.config_service import get_tenant_full_config

    # Get all config params for the tenant
    config = get_tenant_full_config(db, tenant_id)

    # Extract relevant ML parameters with defaults
    return {
        "strong_move_threshold": config.get("STRONG_MOVE_THRESHOLD", 3.0),
        "max_days": config.get("MAX_DAYS", 5),
        "min_days": config.get("MIN_DAYS", 1),
        "confidence_threshold": config.get("CONFIDENCE_THRESHOLD", 0.5),
        "model_type": config.get("MODEL_TYPE", LIGHTGBM),
        # Any other needed parameters
    }


def get_model_params(model_type: str, db: Session = None, tenant_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Get model hyperparameters, from config if available

    Args:
        model_type: Type of model
        db: Database session (optional)
        tenant_id: Tenant ID (optional)

    Returns:
        Dictionary of model parameters
    """
    # Start with default parameters
    params = DEFAULT_PARAMS.get(model_type, {}).copy()

    # If db and tenant_id provided, check for custom hyperparameters in config
    if db and tenant_id:
        from app.services.config_service import get_tenant_config

        # Check for tenant-specific model parameters
        # Example: LIGHTGBM_N_ESTIMATORS, LIGHTGBM_LEARNING_RATE, etc.
        if model_type == LIGHTGBM:
            n_estimators = get_tenant_config(db, tenant_id, "LIGHTGBM_N_ESTIMATORS")
            if n_estimators:
                params["n_estimators"] = int(n_estimators)

            learning_rate = get_tenant_config(db, tenant_id, "LIGHTGBM_LEARNING_RATE")
            if learning_rate:
                params["learning_rate"] = float(learning_rate)

            # Additional parameters could be added here

    return params
