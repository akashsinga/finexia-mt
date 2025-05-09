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
        # List of models that should NOT have tenant_id FK
        tenant_agnostic_models = ["Tenant", "Symbol", "EODData", "FeatureData"]  # Tenants are not tenant-specific  # Global symbol repository  # EOD data is shared  # Features are shared
        if cls.__name__ in tenant_agnostic_models:
            return None
        return Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)


Base = declarative_base(cls=CustomBase)
