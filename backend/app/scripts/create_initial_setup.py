# backend/app/scripts/create_initial_setup.py
import argparse
import sys
import os
from app.scripts.init_system import init_system

from app.core.logger import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize Finexia system")
    parser.add_argument("--username", default="superadmin", help="Superadmin username")
    parser.add_argument("--email", default="superadmin@finexia.com", help="Superadmin email")
    parser.add_argument("--password", required=True, help="Superadmin password")

    args = parser.parse_args()

    try:
        init_system(superadmin_username=args.username, superadmin_email=args.email, superadmin_password=args.password)
        logger.info("System initialized successfully!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error initializing system: {str(e)}")
        sys.exit(1)
