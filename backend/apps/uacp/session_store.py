"""In-process session store for UACP orchestration sessions.

For production multi-instance deployments, swap this out for a
Redis-backed store using the same interface.
"""
from __future__ import annotations
import asyncio
from datetime import datetime
from typing import Dict, Optional
from .models import SessionState, SessionStatus


_sessions: Dict[str, SessionState] = {}
_lock = asyncio.Lock()


async def get_or_create(session_id: str, tenant_id: Optional[str] = None) -> SessionState:
    async with _lock:
        if session_id not in _sessions:
            _sessions[session_id] = SessionState(
                session_id=session_id,
                tenant_id=tenant_id,
            )
        return _sessions[session_id]


async def set_status(session_id: str, status: SessionStatus) -> None:
    async with _lock:
        if session_id in _sessions:
            _sessions[session_id].status = status
            _sessions[session_id].last_active = datetime.utcnow()


async def increment_messages(session_id: str) -> None:
    async with _lock:
        if session_id in _sessions:
            _sessions[session_id].message_count += 1
            _sessions[session_id].last_active = datetime.utcnow()


async def get(session_id: str) -> Optional[SessionState]:
    return _sessions.get(session_id)


async def delete(session_id: str) -> None:
    async with _lock:
        _sessions.pop(session_id, None)


def all_sessions() -> Dict[str, SessionState]:
    return dict(_sessions)
