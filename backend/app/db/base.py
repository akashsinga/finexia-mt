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
        # Skip tenant field for Tenant model itself
        if cls.__name__ == "Tenant":
            return None
        return Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)


Base = declarative_base(cls=CustomBase)

from app.db.models import *