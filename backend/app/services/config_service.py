# backend/app/services/config_service.py
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.db.models.config_param import ConfigParam, DEFAULT_CONFIG
from app.db.models.tenant import Tenant


def get_tenant_config(db: Session, tenant_id: int, key: str) -> Any:
    """
    Get a tenant-specific configuration value.
    Falls back to default if not found.
    """
    param = db.query(ConfigParam).filter(ConfigParam.tenant_id == tenant_id, ConfigParam.key == key).first()

    if param:
        return param.value

    # Return default if exists
    if key in DEFAULT_CONFIG:
        default_config = DEFAULT_CONFIG[key]
        return default_config["value"]

    return None


def get_tenant_full_config(db: Session, tenant_id: int) -> Dict[str, Any]:
    """
    Get all configuration values for a tenant.
    Merges with defaults for any missing values.
    """
    # Start with defaults
    config = {key: item["value"] for key, item in DEFAULT_CONFIG.items()}

    # Override with tenant-specific values
    params = db.query(ConfigParam).filter(ConfigParam.tenant_id == tenant_id).all()
    for param in params:
        config[param.key] = param.value

    return config


def set_tenant_config(db: Session, tenant_id: int, key: str, value: Any) -> ConfigParam:
    """
    Set a tenant-specific configuration value.
    """
    # Check if param already exists
    param = db.query(ConfigParam).filter(ConfigParam.tenant_id == tenant_id, ConfigParam.key == key).first()

    if not param:
        param = ConfigParam(tenant_id=tenant_id, key=key)

    # Set the value based on type
    if isinstance(value, bool):
        param.value_bool = value
        param.value_int = None
        param.value_float = None
        param.value_str = None
    elif isinstance(value, int):
        param.value_bool = None
        param.value_int = value
        param.value_float = None
        param.value_str = None
    elif isinstance(value, float):
        param.value_bool = None
        param.value_int = None
        param.value_float = value
        param.value_str = None
    else:
        param.value_bool = None
        param.value_int = None
        param.value_float = None
        param.value_str = str(value)

    # Set description if this is a known parameter
    if key in DEFAULT_CONFIG:
        param.description = DEFAULT_CONFIG[key]["description"]

    db.add(param)
    db.commit()
    db.refresh(param)
    return param


def initialize_tenant_config(db: Session, tenant_id: int) -> None:
    """
    Initialize default config for a new tenant.
    """
    for key, config in DEFAULT_CONFIG.items():
        param = ConfigParam(tenant_id=tenant_id, key=key, description=config["description"])

        # Set value based on type
        value = config["value"]
        value_type = config["type"]

        if value_type == "bool":
            param.value_bool = value
        elif value_type == "int":
            param.value_int = value
        elif value_type == "float":
            param.value_float = value
        else:  # str
            param.value_str = value

        db.add(param)

    db.commit()
