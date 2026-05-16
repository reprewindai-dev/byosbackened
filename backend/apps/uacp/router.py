"""UACP FastAPI router.

Mount in your main app:
    from apps.uacp import router as uacp_router
    app.include_router(uacp_router, prefix="/uacp", tags=["uacp"])
"""
from __future__ import annotations
import uuid
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from .models import (
    OrchestrationRequest,
    OrchestrationResult,
    SessionState,
    MeshTopology,
    MeshNode,
)
from .orchestrator import run_orchestration, stream_orchestration
from . import session_store

router = APIRouter()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health", summary="UACP health check")
async def health():
    return {"status": "ok", "module": "uacp", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

@router.post("/orchestrate", response_model=OrchestrationResult, summary="Run orchestration (non-streaming)")
async def orchestrate(req: OrchestrationRequest):
    """Submit a prompt to the UACP cognitive engine. Returns full result."""
    session_id = req.session_id or str(uuid.uuid4())
    req.session_id = session_id

    await session_store.get_or_create(session_id, req.tenant_id)
    await session_store.set_status(session_id, "interrogating")  # type: ignore

    try:
        result = await run_orchestration(req)
        await session_store.set_status(session_id, "phase_locked")  # type: ignore
        await session_store.increment_messages(session_id)
        return result
    except Exception as exc:
        await session_store.set_status(session_id, "error")  # type: ignore
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/orchestrate/stream", summary="Run orchestration (SSE streaming)")
async def orchestrate_stream(req: OrchestrationRequest):
    """Submit a prompt and receive Server-Sent Events with real-time telemetry + token stream."""
    session_id = req.session_id or str(uuid.uuid4())
    req.session_id = session_id
    req.stream = True

    await session_store.get_or_create(session_id, req.tenant_id)
    await session_store.set_status(session_id, "interrogating")  # type: ignore

    async def event_generator():
        try:
            async for event in stream_orchestration(req):
                payload = json.dumps(event.dict(), default=str)
                yield f"data: {payload}\n\n"
            await session_store.set_status(session_id, "phase_locked")  # type: ignore
            await session_store.increment_messages(session_id)
        except Exception as exc:
            await session_store.set_status(session_id, "error")  # type: ignore
            error_payload = json.dumps({"event": "error", "data": {"message": str(exc)}})
            yield f"data: {error_payload}\n\n"
        finally:
            yield "data: {\"event\": \"done\"}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

@router.get("/sessions", summary="List all active UACP sessions")
async def list_sessions():
    sessions = session_store.all_sessions()
    return {"sessions": [s.dict() for s in sessions.values()], "count": len(sessions)}


@router.get("/sessions/{session_id}", response_model=SessionState, summary="Get session state")
async def get_session(session_id: str):
    session = await session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/sessions/{session_id}", summary="Terminate a session")
async def delete_session(session_id: str):
    await session_store.delete(session_id)
    return {"deleted": session_id}


# ---------------------------------------------------------------------------
# MCP Mesh Topology
# ---------------------------------------------------------------------------

@router.get("/mesh", response_model=MeshTopology, summary="Get MCP mesh topology")
async def get_mesh(session_id: Optional[str] = Query(default=None)):
    """Returns the current MCP host-client-server mesh topology."""
    nodes = [
        MeshNode(
            id="uacp-host",
            role="host",
            label="UACP Host",
            status="active",
            capabilities=["orchestrate", "session_manage", "telemetry"],
        ),
        MeshNode(
            id="mcp-client",
            role="client",
            label="MCP Client Translator",
            status="active",
            capabilities=["protocol_bridge", "capability_exchange", "tool_routing"],
        ),
        MeshNode(
            id="gemini-server",
            role="server",
            label="Gemini Context Server",
            status="active",
            capabilities=["chat", "stream", "embed"],
        ),
        MeshNode(
            id="byos-server",
            role="server",
            label="BYOS Resource Server",
            status="active",
            capabilities=["tenant_context", "tool_registry", "data_access"],
        ),
    ]
    edges = [
        {"from": "uacp-host", "to": "mcp-client", "label": "orchestration_request"},
        {"from": "mcp-client", "to": "gemini-server", "label": "mcp_session"},
        {"from": "mcp-client", "to": "byos-server", "label": "mcp_session"},
        {"from": "gemini-server", "to": "mcp-client", "label": "context_response"},
        {"from": "byos-server", "to": "mcp-client", "label": "resource_response"},
        {"from": "mcp-client", "to": "uacp-host", "label": "synthesised_plan"},
    ]
    return MeshTopology(nodes=nodes, edges=edges, session_id=session_id)
