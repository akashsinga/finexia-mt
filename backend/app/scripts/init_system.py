# backend/app/scripts/init_system.py
import logging
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.user_service import create_superadmin
from app.services.tenant_service import create_tenant
from app.schemas.tenant import TenantCreate
from app.db.models.tenant import Tenant
from app.db.models.user import User

logger = logging.getLogger(__name__)


def init_system(superadmin_username: str, superadmin_email: str, superadmin_password: str):
    """Initialize the system with superadmin and default tenant"""
    db = SessionLocal()
    try:
        # Check if system is already initialized
        existing_superadmin = db.query(User).filter(User.is_superadmin == True).first()
        if existing_superadmin:
            logger.info("System already initialized with superadmin")
            return

        # Create default tenant (Finexia) FIRST
        logger.info("Creating default Finexia tenant")
        default_tenant = TenantCreate(name="Finexia", slug="finexia", plan="enterprise", max_symbols=None)
        tenant = create_tenant(db=db, tenant=default_tenant)

        # Create superadmin (now tied to the tenant)
        logger.info(f"Creating superadmin user: {superadmin_username}")
        superadmin = create_superadmin(db=db, username=superadmin_username, email=superadmin_email, password=superadmin_password, full_name="System Administrator",tenant_id=tenant.id)

        # Create admin user for Finexia tenant
        from app.schemas.user import UserCreate
        from app.services.user_service import create_user

        # logger.info("Creating admin user for Finexia tenant")
        # admin_user = UserCreate(username="admin", email="admin@finexia.com", password="admin123", full_name="Finexia Administrator", is_admin=True, tenant_id=tenant.id)  # Should be changed after first login
        # create_user(db=db, user=admin_user)

        logger.info("System initialization completed successfully")
    except Exception as e:
        logger.error(f"Error initializing system: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()