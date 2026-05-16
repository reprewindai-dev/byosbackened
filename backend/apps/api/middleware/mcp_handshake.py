"""MCP Handshake Middleware — UACP Control Plane.

Enforces Model Context Protocol (MCP) version negotiation and session identity
on all UACP-controlled surfaces:
  - /api/v1/autonomous/*
  - /api/v1/internal/uacp/*
  - /api/v1/internal/operators/*

Non-UACP routes pass through with no overhead.

MCP spec: https://spec.modelcontextprotocol.io/specification/2025-06-18/
"""
from __future__ import annotations

import json
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

SUPPORTED_MCP_VERSIONS: frozenset[str] = frozenset(
    {"2025-06-18", "2025-03-26", "2024-11-05"}
)

# Surfaces where MCP handshake is enforced
UACP_PREFIXES: tuple[str, ...] = (
    "/api/v1/autonomous",
    "/api/v1/internal/uacp",
    "/api/v1/internal/operators",
)

# Headers that callers MUST supply on UACP surfaces
REQUIRED_HEADERS: tuple[str, ...] = (
    "x-mcp-protocol-version",
    "x-uacp-host-id",
    "x-uacp-session-id",
)


def _is_uacp_surface(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in UACP_PREFIXES)


class MCPHandshakeMiddleware(BaseHTTPMiddleware):
    """Enforce MCP capability negotiation on UACP control surfaces.

    On every request to a UACP surface:
      1. All REQUIRED_HEADERS must be present.
      2. x-mcp-protocol-version must be in SUPPORTED_MCP_VERSIONS.
      3. A session ID is echoed back; a fresh one is minted if absent.
      4. Phase state and host ID are stamped on every response.

    Non-UACP requests skip all checks and have zero overhead.
    """

    def __init__(self, app: ASGIApp, host_id: str = "uacp-host-main") -> None:
        super().__init__(app)
        self.host_id = host_id

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        path = request.url.path

        if not _is_uacp_surface(path):
            return await call_next(request)

        # --- Validate required headers ---
        missing = [h for h in REQUIRED_HEADERS if not request.headers.get(h)]
        if missing:
            return JSONResponse(
                status_code=426,
                content={
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32600,
                        "message": "mcp_handshake_required",
                        "data": {
                            "missing_headers": missing,
                            "required_headers": list(REQUIRED_HEADERS),
                            "supported_versions": sorted(SUPPORTED_MCP_VERSIONS),
                            "docs": "https://spec.modelcontextprotocol.io/specification/2025-06-18/",
                        },
                    },
                },
                headers={"x-uacp-host-id": self.host_id},
            )

        # --- Validate protocol version ---
        protocol = request.headers.get("x-mcp-protocol-version", "")
        if protocol not in SUPPORTED_MCP_VERSIONS:
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32600,
                        "message": "unsupported_mcp_protocol_version",
                        "data": {
                            "received": protocol,
                            "supported_versions": sorted(SUPPORTED_MCP_VERSIONS),
                        },
                    },
                },
                headers={"x-uacp-host-id": self.host_id},
            )

        # --- Resolve / mint session ID ---
        session_id = request.headers.get("x-uacp-session-id") or f"sess_{uuid.uuid4().hex[:12]}"
        host_id = request.headers.get("x-uacp-host-id") or self.host_id

        # Attach to request state so downstream routers can read it
        request.state.uacp_session_id = session_id
        request.state.uacp_host_id = host_id
        request.state.mcp_protocol_version = protocol

        # --- Handle MCP notification headers for refresh cycles ---
        tools_changed = request.headers.get("x-mcp-notify-tools-changed") == "true"
        resources_updated = request.headers.get("x-mcp-notify-resources-updated") == "true"

        response = await call_next(request)

        # --- Stamp UACP identity on every response ---
        response.headers["x-uacp-session-id"] = session_id
        response.headers["x-uacp-host-id"] = host_id
        response.headers["x-mcp-protocol-version"] = protocol

        if tools_changed:
            response.headers["x-uacp-refresh-cycle"] = "tools-changed"
        if resources_updated:
            response.headers["x-uacp-zeno-probe"] = "scheduled"

        return response
