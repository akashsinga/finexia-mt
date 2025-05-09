# backend/app/db/models/model_performance.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class ModelPerformance(Base):
    __tablename__ = "model_performances"
    __table_args__ = (
        Index("idx_model_perf_tenant_model", "tenant_id", "model_id"),
        Index("idx_model_perf_date", "evaluation_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("prediction_models.id"), nullable=False)
    evaluation_date = Column(DateTime, default=func.now(), nullable=False)
    
    # Performance metrics
    accuracy = Column(Float, nullable=False)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    roc_auc = Column(Float, nullable=True)
    
    # Additional metrics
    mse = Column(Float, nullable=True)  # Mean Squared Error
    rmse = Column(Float, nullable=True)  # Root Mean Squared Error
    mae = Column(Float, nullable=True)   # Mean Absolute Error
    r2 = Column(Float, nullable=True)    # R-squared
    
    # Training details
    train_samples = Column(Integer, nullable=True)
    test_samples = Column(Integer, nullable=True)
    training_time_seconds = Column(Float, nullable=True)
    
    # Configuration hash for reproducibility
    config_hash = Column(String, nullable=True)
    hyperparameters = Column(String, nullable=True)  # JSON string of hyperparameters
    
    # Relations
    model = relationship("PredictionModel", back_populates="performances")

    # tenant_id comes from Base class

    @property
    def performance_summary(self):
        """Get a summary of the model performance metrics."""
        return {
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "roc_auc": self.roc_auc
        }