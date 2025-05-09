# backend/app/api/routers/auth.py
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.session import get_db_session
from app.services.auth_service import authenticate_user, create_access_token
from app.config import settings
from app.schemas.token import Token

router = APIRouter()


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db_session)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expires_at = datetime.utcnow() + access_token_expires

    token_data = {
        "sub": user.username,
        "is_admin": user.is_admin,
        "is_superadmin": user.is_superadmin,
    }

    # Add tenant info to token if user belongs to a tenant
    tenant_slug = None
    if user.tenant_id and user.tenant:
        token_data["tenant_id"] = user.tenant_id
        tenant_slug = user.tenant.slug

    access_token = create_access_token(data=token_data, expires_delta=access_token_expires)

    return Token(access_token=access_token, token_type="bearer", expires_at=expires_at, tenant_slug=tenant_slug)
