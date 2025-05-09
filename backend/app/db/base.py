# backend/app/db/base.py
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base, declared_attr


class CustomBase:
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True, index=True)

    @declared_attr
    def tenant_id(cls):
        # Skip tenant field for specified tenant-agnostic models
        tenant_agnostic_models = ["Tenant", "Symbol", "EODData", "FeatureData"]
        if cls.__name__ in tenant_agnostic_models:
            return None
        return Column(Integer, ForeignKey("tenant.id"), nullable=False, index=True)


Base = declarative_base(cls=CustomBase)
