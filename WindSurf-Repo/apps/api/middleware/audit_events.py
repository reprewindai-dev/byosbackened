"""Middleware to append immutable audit events for HTTP requests."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

from sqlalchemy.orm import Session

from db.session import SessionLocal
from core.audit.audit_logger import get_audit_event_logger


class AuditEventsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.logger = get_audit_event_logger()

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        skip = (
            path.startswith("/static/")
            or path in {"/", "/health", "/metrics"}
            or path.endswith("/openapi.json")
            or path.endswith("/docs")
            or path.endswith("/redoc")
        )

        if skip:
            return await call_next(request)

        response = None
        exc: Exception | None = None
        should_log = True
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            exc = e
            raise
        finally:
            if skip:
                should_log = False

            if not should_log:
                pass
            else:

                db: Session = SessionLocal()
                try:
                    workspace_id = getattr(request.state, "workspace_id", None)
                    user_id = getattr(request.state, "user_id", None)
                    actor_type = "user" if user_id else "system"

                    organization_id = getattr(request.state, "organization_id", None)

                    status_code = (
                        str(getattr(response, "status_code", None))
                        if response is not None
                        else None
                    )
                    success = (
                        response is not None and 200 <= response.status_code < 500 and exc is None
                    )

                    self.logger.append_event(
                        db,
                        workspace_id=workspace_id,
                        organization_id=organization_id,
                        actor_user_id=user_id,
                        actor_type=actor_type,
                        action="http.request",
                        resource_type="http",
                        resource_id=f"{request.method} {path}",
                        request_id=request.headers.get("x-request-id"),
                        ip_address=request.client.host if request.client else None,
                        user_agent=request.headers.get("user-agent"),
                        success=success,
                        status_code=status_code,
                        details={
                            "method": request.method,
                            "path": path,
                            "query": str(request.url.query),
                        },
                    )
                finally:
                    db.close()
