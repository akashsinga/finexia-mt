# backend/app/api/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db_session
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.user_service import create_user, get_user, get_users_by_tenant, update_user
from app.api.deps import get_current_user, get_current_active_admin, get_current_tenant

router = APIRouter()


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_new_user(user: UserCreate, db: Session = Depends(get_db_session), current_user=Depends(get_current_active_admin), tenant=Depends(get_current_tenant)):
    """Create a new user in the current tenant"""
    # Ensure user is created in the current tenant
    user.tenant_id = tenant.id
    return create_user(db, user)


@router.get("/", response_model=List[UserResponse])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db_session), current_user=Depends(get_current_active_admin), tenant=Depends(get_current_tenant)):
    """Get all users in the current tenant"""
    return get_users_by_tenant(db, tenant.id, skip, limit)


@router.get("/me", response_model=UserResponse)
def read_user_me(current_user=Depends(get_current_user)):
    """Get current user information"""
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db_session), current_user=Depends(get_current_active_admin), tenant=Depends(get_current_tenant)):
    """Get a specific user in the current tenant"""
    user = get_user(db, user_id)
    if not user or user.tenant_id != tenant.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user_endpoint(user_id: int, user_data: UserUpdate, db: Session = Depends(get_db_session), current_user=Depends(get_current_active_admin), tenant=Depends(get_current_tenant)):
    """Update a user in the current tenant"""
    # Check if user exists and belongs to this tenant
    user = get_user(db, user_id)
    if not user or user.tenant_id != tenant.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Regular admins cannot modify other admins
    if user.is_admin and not current_user.is_superadmin and user.id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Regular admins cannot modify other admins")

    # Update user
    updated_user = update_user(db, user_id, user_data)
    return updated_user
