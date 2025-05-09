# backend/app/db/models/config_param.py
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, UniqueConstraint
from app.db.base import Base

# Default configuration values
DEFAULT_CONFIG = {
    "MAX_DAYS": {"value": 5, "type": "int", "description": "Maximum days to consider for predictions"},
    "STRONG_MOVE_THRESHOLD": {"value": 3.0, "type": "float", "description": "Threshold for considering a move as strong (%)"},
    "MODEL_TYPE": {"value": "lightgbm", "type": "str", "description": "Default model type for predictions"},
    "MIN_DAYS": {"value": 1, "type": "int", "description": "Minimum days to consider for predictions"},
    "CONFIDENCE_THRESHOLD": {"value": 0.5, "type": "float", "description": "Minimum confidence threshold for predictions"},
    "TRAINING_FREQUENCY": {"value": "daily", "type": "str", "description": "Model training frequency"},
    "CLIENT_ID": {"value": "", "type": "str", "description": "Client identifier for API calls"},
    "API_KEY": {"value": "", "type": "str", "description": "API key for data import"},
}


class ConfigParam(Base):
    __tablename__ = "config_params"
    __table_args__ = (UniqueConstraint("tenant_id", "key", name="unique_tenant_param"),)

    key = Column(String, nullable=False, index=True)
    value_str = Column(String, nullable=True)
    value_int = Column(Integer, nullable=True)
    value_float = Column(Float, nullable=True)
    value_bool = Column(Boolean, nullable=True)
    description = Column(String, nullable=True)

    @property
    def value(self):
        """Return the value in the appropriate type"""
        if self.value_bool is not None:
            return self.value_bool
        if self.value_int is not None:
            return self.value_int
        if self.value_float is not None:
            return self.value_float
        return self.value_str
