# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.config import settings
from app.api.middleware.tenant import TenantMiddleware
from app.api.routers import auth, users, tenants, symbols, config, system
from app.websockets.router import router as websocket_router
from app.db.base import Base
from app.db.session import engine
from app.core.logger import get_logger

logger = get_logger(__name__)

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize features, connections
    logger.info(f"Starting {settings.APP_NAME} API Server")

    # Check if system is initialized
    from app.db.session import SessionLocal
    from app.db.models.user import User

    db = SessionLocal()
    try:
        superadmin_exists = db.query(User).filter(User.is_superadmin == True).first() is not None
        if not superadmin_exists:
            # Auto-initialize if configured
            from app.scripts.init_system import init_system

            init_system(superadmin_username=os.environ.get("INIT_SUPERADMIN_USERNAME", "superadmin"), superadmin_email=os.environ.get("INIT_SUPERADMIN_EMAIL", "akashsinga@gmail.com"), superadmin_password=os.environ.get("INIT_SUPERADMIN_PASSWORD", "password"))
    finally:
        db.close()

    yield

    # Shutdown code
    logger.info(f"Shutting down {settings.APP_NAME} API Server")


# Initialize FastAPI app with lifespan
app = FastAPI(title=settings.APP_NAME, description="Multi-tenant Stock Market Intelligence API", version="1.0.0", lifespan=lifespan)

# Adding CORS middleware
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"], expose_headers=["Content-Type", "Authorization", settings.TENANT_HEADER_NAME], max_age=86400)

# Add tenant middleware
app.add_middleware(TenantMiddleware)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["users"])
app.include_router(tenants.router, prefix=f"{settings.API_V1_PREFIX}/tenants", tags=["tenants"])
app.include_router(symbols.router, prefix=f"{settings.API_V1_PREFIX}/symbols", tags=["symbols"])
app.include_router(config.router, prefix=f"{settings.API_V1_PREFIX}/config", tags=["config"])
app.include_router(system.router, prefix=f"{settings.API_V1_PREFIX}/system", tags=["system"])

# Future routers to be added when implemented:
# app.include_router(predictions.router, prefix=f"{settings.API_V1_PREFIX}/predictions", tags=["predictions"])
# app.include_router(historical.router, prefix=f"{settings.API_V1_PREFIX}/historical", tags=["historical"])
# app.include_router(models_router.router, prefix=f"{settings.API_V1_PREFIX}/models", tags=["models"])

app.include_router(websocket_router)


@app.get("/", tags=["root"])
async def root():
    """Root endpoint to check API status"""
    return {"status": "online", "api_version": "1.0.0", "system_name": settings.APP_NAME, "documentation": "/docs"}


# Run the application with: uvicorn app.main:app --reload
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
