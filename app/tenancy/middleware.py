import uuid
from contextvars import ContextVar

from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings

current_tenant_id: ContextVar[uuid.UUID | None] = ContextVar("current_tenant_id", default=None)


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        tenant_id = None

        # Try X-Tenant-ID header first
        header_tenant = request.headers.get("X-Tenant-ID")
        if header_tenant:
            try:
                tenant_id = uuid.UUID(header_tenant)
            except ValueError:
                pass

        # If no header, try to extract from JWT
        if not tenant_id:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                try:
                    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
                    tid = payload.get("tenant_id")
                    if tid:
                        tenant_id = uuid.UUID(tid)
                except (JWTError, ValueError):
                    pass

        token = current_tenant_id.set(tenant_id)
        try:
            response = await call_next(request)
            return response
        finally:
            current_tenant_id.reset(token)
