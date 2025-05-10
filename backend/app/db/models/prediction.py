# backend/app/db/models/prediction.py
from sqlalchemy import Column, String, Integer, Float, Date, Boolean, UniqueConstraint, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base
from enum import Enum as PythonEnum

class DirectionEnum(str, PythonEnum):
    UP = "UP"
    DOWN = "DOWN"
    NONE = "NONE"

class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "symbol_id", "date", name="unique_tenant_symbol_prediction_date"),
        Index("idx_prediction_tenant_symbol_date", "tenant_id", "symbol_id", "date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    strong_move_confidence = Column(Float, nullable=False)
    direction_prediction = Column(String, nullable=True)
    direction_confidence = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    model_config_hash = Column(String, nullable=True)

    # Verification fields
    verified = Column(Boolean, default=False)
    verification_date = Column(Date, nullable=True)
    actual_move_percent = Column(Float, nullable=True)
    actual_direction = Column(String, nullable=True)
    days_to_fulfill = Column(Integer, nullable=True)

    # tenant_id comes from Base class

    # Relationships
    symbol = relationship("Symbol", back_populates="predictions")
