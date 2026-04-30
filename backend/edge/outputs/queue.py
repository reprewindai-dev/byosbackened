"""Queue output adapter placeholder."""

from __future__ import annotations


async def enqueue(msg):
    """Queue integration placeholder."""
    return {"status": "queued", "message": "Queue connector not enabled in phase 1", "data": msg.payload if hasattr(msg, "payload") else msg}
