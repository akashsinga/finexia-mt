# backend/app/db/models/eod_data.py
from sqlalchemy import Column, String, Integer, Float, Date, Boolean, BigInteger, UniqueConstraint, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class EODData(Base):
    __tablename__ = "eod_data"
    __table_args__ = (
        UniqueConstraint("symbol_id", "date", name="unique_symbol_eod_date"),
        Index("idx_eod_symbol_date", "symbol_id", "date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    change_percent = Column(Float, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    symbol = relationship("Symbol", back_populates="eod_data")
