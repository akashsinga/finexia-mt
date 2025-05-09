# backend/app/services/user_service.py
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import HTTPException, status
from app.db.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.auth_service import get_password_hash


def get_user(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()


def get_users_by_tenant(db: Session, tenant_id: int, skip: int = 0, limit: int = 100) -> List[User]:
    """Get users belonging to a tenant"""
    return db.query(User).filter(User.tenant_id == tenant_id).offset(skip).limit(limit).all()


def create_user(db: Session, user: UserCreate) -> User:
    """Create a new user"""
    # Check if username or email already exists
    if get_user_by_username(db, user.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Username '{user.username}' already taken")

    if get_user_by_email(db, user.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Email '{user.email}' already registered")

    # Hash the password
    hashed_password = get_password_hash(user.password)

    # Create user
    db_user = User(email=user.email, username=user.username, hashed_password=hashed_password, full_name=user.full_name, is_admin=user.is_admin, tenant_id=user.tenant_id, is_active=True)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


def update_user(db: Session, user_id: int, user_data: UserUpdate) -> Optional[User]:
    """Update user information"""
    db_user = get_user(db, user_id)
    if not db_user:
        return None

    # Update user fields
    update_data = user_data.dict(exclude_unset=True)

    # Hash password if provided
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)

    return db_user


def create_superadmin(db: Session, username: str, email: str, password: str, full_name: Optional[str] = None, tenant_id: Optional[int] = None) -> User:
    """Create a superadmin user"""
    # Check if username or email already exists
    if get_user_by_username(db, username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Username '{username}' already taken")

    if get_user_by_email(db, email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Email '{email}' already registered")

    # Hash the password
    hashed_password = get_password_hash(password)

    # Create superadmin user (with tenant_id)
    db_user = User(email=email, username=username, hashed_password=hashed_password, full_name=full_name, is_admin=True, is_superadmin=True, tenant_id=tenant_id, is_active=True)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user
