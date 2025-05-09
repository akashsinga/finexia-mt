# backend/app/db/models/feature_data.py
from sqlalchemy import Column, Integer, Float, Date, String, ForeignKey, UniqueConstraint, Index, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class FeatureData(Base):
    __tablename__ = "feature_data"
    __table_args__ = (
        UniqueConstraint("symbol_id", "date", name="unique_symbol_feature_date"),
        Index("idx_feature_symbol_date", "symbol_id", "date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    
    # Technical indicators
    week_day = Column(Integer)
    volatility_squeeze = Column(Float)
    trend_zone_strength = Column(Float)
    range_compression_ratio = Column(Float)
    volume_spike_ratio = Column(Float)
    body_to_range_ratio = Column(Float)
    distance_from_ema_5 = Column(Float)
    gap_pct = Column(Float)
    return_3d = Column(Float)
    atr_5 = Column(Float)
    hl_range = Column(Float)
    rsi_14 = Column(Float)
    close_ema50_gap_pct = Column(Float)
    open_gap_pct = Column(Float)
    macd_histogram = Column(Float)
    atr_14_normalized = Column(Float)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    symbol = relationship("Symbol")