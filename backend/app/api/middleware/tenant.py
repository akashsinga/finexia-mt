# backend/app/api/middleware/tenant.py
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.db.session import get_db_session


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tenant_header = request.headers.get("X-Tenant")
        tenant_url = request.path_params.get("tenant_slug")
        tenant_id = tenant_header or tenant_url

        if not tenant_id:
            return await call_next(request)

        # Store tenant in request state
        session = next(get_db_session())
        from app.db.models.tenant import Tenant

        tenant = session.query(Tenant).filter(Tenant.slug == tenant_id, Tenant.is_active == True).first()

        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found or inactive")

        request.state.tenant = tenant
        response = await call_next(request)
        return response
