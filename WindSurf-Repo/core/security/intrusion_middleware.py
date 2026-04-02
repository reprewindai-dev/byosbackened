"""Intrusion detection middleware."""

from fastapi import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from core.security.intrusion_detection import IntrusionDetectionSystem
from core.security.input_validation import InputValidator
from db.session import SessionLocal
import logging
import asyncio

logger = logging.getLogger(__name__)


class IntrusionDetectionMiddleware(BaseHTTPMiddleware):
    """Middleware to detect and block intrusion attempts."""

    def __init__(self, app):
        super().__init__(app)
        self.ids = IntrusionDetectionSystem()
        self.validator = InputValidator()

    async def dispatch(self, request: Request, call_next):
        """Check for intrusion attempts."""
        db = SessionLocal()

        try:
            request_path = request.url.path
            request_method = request.method
            headers = dict(request.headers)

            body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body_bytes = await request.body()
                    body = body_bytes.decode("utf-8", errors="ignore")

                    # Restore the body stream so downstream handlers can still
                    # call request.body(). Starlette 0.27 uses request._receive
                    # internally via call_next — return the cached bytes each time.
                    async def receive():
                        return {"type": "http.request", "body": body_bytes, "more_body": False}

                    request._receive = receive
                except Exception:
                    pass

            ip_address = request.client.host if request.client else None
            user_id = getattr(request.state, "user_id", None)
            workspace_id = getattr(request.state, "workspace_id", None)

            validation_errors = []

            # ── Path validation ──────────────────────────────────────────────
            # API route paths are server-defined and may contain SQL-keyword
            # substrings (e.g. /ai/execute matches EXECUTE).
            # Only validate XSS, command injection, and path traversal for paths.
            is_valid, error = self.validator.validate_string(
                request_path,
                allow_sql=True,            # routes are not user input
                allow_xss=False,
                allow_command_injection=False,
                allow_path_traversal=False,
            )
            if not is_valid:
                validation_errors.append(f"Path: {error}")

            # ── Header validation ────────────────────────────────────────────
            safe_headers = {
                "accept", "accept-encoding", "accept-language", "connection",
                "content-type", "content-length", "host", "referer", "user-agent",
                "origin", "cache-control", "pragma", "upgrade", "via",
                "x-forwarded-for", "x-real-ip", "x-requested-with",
                "authorization", "cookie", "x-workspace-id",
                "sec-fetch-site", "sec-fetch-mode", "sec-fetch-dest",
                "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform",
            }
            for header_name, header_value in headers.items():
                if header_name.lower() in safe_headers:
                    continue
                is_valid, error = self.validator.validate_string(
                    header_value, allow_sql=False, allow_xss=False,
                )
                if not is_valid:
                    validation_errors.append(f"Header {header_name}: {error}")

            # ── Body validation ──────────────────────────────────────────────
            if body:
                is_valid, error = self.validator.validate_string(
                    body, allow_sql=False, allow_xss=False,
                    allow_command_injection=False,
                )
                if not is_valid:
                    validation_errors.append(f"Body: {error}")

            # ── Block invalid input ──────────────────────────────────────────
            # IMPORTANT: return JSONResponse, NOT raise HTTPException.
            # Raising inside BaseHTTPMiddleware on Starlette ≤0.27 causes
            # anyio.EndOfStream to propagate to the ASGI transport layer.
            if validation_errors:
                logger.warning(
                    f"Input validation failed: ip={ip_address}, "
                    f"path={request_path}, errors={validation_errors}"
                )
                return JSONResponse(
                    status_code=400,
                    content={"detail": f"Invalid input detected: {validation_errors[0]}"},
                )

            # ── Intrusion detection ──────────────────────────────────────────
            try:
                intrusion_result = self.ids.detect_intrusion(
                    db=db,
                    request_path=request_path,
                    request_method=request_method,
                    headers=headers,
                    body=body,
                    ip_address=ip_address,
                    user_id=user_id,
                    workspace_id=workspace_id,
                )

                if intrusion_result.get("is_intrusion"):
                    threat_level = intrusion_result.get("threat_level", "low")
                    if self.ids.should_block(threat_level):
                        logger.critical(
                            f"Intrusion blocked: level={threat_level}, "
                            f"ip={ip_address}, reason={intrusion_result.get('reason')}"
                        )
                        return JSONResponse(
                            status_code=403,
                            content={"detail": "Request blocked: Security threat detected"},
                        )
                    delay = self.ids.get_response_delay(threat_level)
                    if delay > 0:
                        await asyncio.sleep(delay)
            except Exception as ids_err:
                logger.warning(f"IDS check failed (non-blocking): {ids_err}")

            response = await call_next(request)
            return response

        except Exception as e:
            logger.error(f"IntrusionDetectionMiddleware unhandled: {e}")
            return await call_next(request)

        finally:
            db.close()
