# backend/app/db/models/prediction_model.py
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base
from enum import Enum as PythonEnum


class ModelTypeEnum(str, PythonEnum):
    LIGHTGBM = "lightgbm"
    RANDOM_FOREST = "random_forest"
    XGBOOST = "xgboost"
    NEURAL_NETWORK = "neural_network"


class PredictionModel(Base):
    __tablename__ = "prediction_models"
    __table_args__ = (
        Index("idx_model_tenant_symbol", "tenant_id", "symbol_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    name = Column(String, nullable=False)
    model_type = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    version = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Path to saved model files
    model_path = Column(String, nullable=True)
    
    # Latest metrics
    current_accuracy = Column(Float, nullable=True)
    
    # Relations
    symbol = relationship("Symbol", back_populates="models")
    performances = relationship("ModelPerformance", back_populates="model", cascade="all, delete-orphan")
    
    # tenant_id comes from Base class
    
    def __repr__(self):
        return f"<PredictionModel(id={self.id}, name='{self.name}', type='{self.model_type}')>"