"""AI output adapter for the edge routing engine."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from core.config import get_settings
from edge.schemas.edge_message import EdgeMessage

settings = get_settings()


def _format_prompt(payload: dict) -> str:
    if "prompt" in payload and isinstance(payload["prompt"], str):
        return payload["prompt"].strip()
    if "temperature" in payload and "status" in payload:
        return f"Device {payload.get('device','unknown')} status={payload.get('status')} temp={payload.get('temperature')}"
    return json.dumps(payload, sort_keys=True)


def _get_bedrock_client():
    kwargs = {}
    if settings.aws_default_region:
        kwargs["region_name"] = settings.aws_default_region
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client("bedrock-runtime", **kwargs)


async def send_to_ai(msg: EdgeMessage) -> dict:
    """
    Run edge payload through the existing AI stack.

    Returns a normalized response envelope and preserves payload metadata.
    """
    if not (settings.aws_access_key_id and settings.aws_secret_access_key):
        # Graceful fallback so edge does not fail hard when Bedrock is not configured.
        return {
            "status": "processed",
            "route": "edge_ai",
            "workspace": msg.source,
            "protocol": msg.protocol,
            "alert": True,
            "ai_processed": False,
            "reason": "missing_aws_credentials",
            "echo": msg.payload,
            "timestamp": datetime.utcnow().isoformat(),
        }

    payload_prompt = _format_prompt(msg.payload)
    request_id = f"edge-ai-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:10]}"
    client = _get_bedrock_client()

    try:
        response = client.converse(
            modelId="meta.llama3-8b-instruct-v1:0",
            messages=[
                {
                    "role": "user",
                    "content": [{"text": payload_prompt}],
                }
            ],
            inferenceConfig={"maxTokens": 256},
        )
        response_text = "".join(
            item.get("text", "")
            for item in response.get("output", {}).get("message", {}).get("content", [])
            if isinstance(item, dict)
        ).strip()
        usage = response.get("usage", {}) or {}
        return {
            "status": "processed",
            "route": "edge_ai",
            "workspace": msg.source,
            "protocol": msg.protocol,
            "request_id": request_id,
            "tokens_output": int(usage.get("outputTokens", 0) or 0),
            "response": response_text,
            "raw": response,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (ClientError, BotoCoreError) as exc:
        return {
            "status": "error",
            "route": "edge_ai",
            "workspace": msg.source,
            "protocol": msg.protocol,
            "request_id": request_id,
            "detail": "ai_forwarding_failed",
            "raw_error": str(exc),
            "timestamp": datetime.utcnow().isoformat(),
        }
