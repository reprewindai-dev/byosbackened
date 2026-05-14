"""QStash webhook receiver for durable UACP background jobs."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from core.services.qstash_dispatch import receiver_configured, verify_qstash_signature


router = APIRouter(tags=["qstash-webhooks"])


@router.post("/webhooks/qstash/uacp-job", include_in_schema=False)
async def qstash_uacp_job(request: Request) -> dict[str, Any]:
    body = await request.body()
    if not body:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty QStash payload")
    signature = request.headers.get("Upstash-Signature") or request.headers.get("upstash-signature")
    if not signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Upstash-Signature header")
    if not receiver_configured():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="QStash receiver is not configured")
    if not verify_qstash_signature(body=body, signature=signature, url=str(request.url)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid QStash signature")
    try:
        event = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid QStash JSON payload") from exc

    return {
        "ok": True,
        "accepted": True,
        "job_type": event.get("job_type"),
        "frame_hash": event.get("frame_hash"),
    }
