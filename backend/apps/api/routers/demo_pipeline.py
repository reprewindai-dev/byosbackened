"""
Public Veklom Live Pipeline Theater ? SSE stream.

GET /api/v1/demo/pipeline/stream

Emits a chronological stream of control-plane events so the landing page can
render the request moving through Veklom in real time:

    request_received ? zero_trust_check ? rate_limit_check ? token_budget_check
    ? circuit_breaker_check ? provider_selected ? (ollama_attempt | ollama_unavailable
    ? circuit_breaker_opened ? groq_fallback) ? redis_memory_check ? token_delta*
    ? response_complete ? audit_written ? cost_recorded ? done

Constraints (demo safety):
    - No auth, rate-limited by IP (5 req / 60s)
    - Prompt length capped (800 chars)
    - Output capped (250 tokens)
    - Hardened system prompt ? no secrets, no backend control, no arbitrary model
    - No persistent memory writes ? scoped ephemeral Redis key, 60s TTL
    - `force_fallback=true` simulates Ollama outage so the circuit breaker path
      can be demonstrated without killing the real production Ollama container.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from typing import Iterable, Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from core.config import get_settings
from core.llm.circuit_breaker import get_state as cb_get_state, status_dict as cb_status
from core.llm.groq_fallback import GroqFallbackError, call_groq
from core.llm.ollama_client import OllamaClient, OllamaError
from core.redis_pool import get_redis

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["demo"])

# ?? Demo guardrails ???????????????????????????????????????????????????????????
_DEMO_PROMPT_MAX_CHARS = 800
_DEMO_OUTPUT_MAX_TOKENS = 250
_DEMO_RATE_LIMIT_WINDOW_SEC = 60
_DEMO_RATE_LIMIT_MAX_HITS = 5
_DEMO_EPHEMERAL_TTL_SEC = 60

_VERTICAL_SYSTEM_PROMPTS = {
    "legal": (
        "You are Veklom's governed AI control plane demo. Answer as a privacy-first "
        "legal operations copilot. Cite the controls (redaction, retention, audit) "
        "you would enforce. Be terse ? under 120 words."
    ),
    "medical": (
        "You are Veklom's governed AI control plane demo. Answer as a HIPAA-aware "
        "clinical-ops assistant. Note which PHI controls and audit events would fire. "
        "Be terse ? under 120 words."
    ),
    "finance": (
        "You are Veklom's governed AI control plane demo. Answer as a SOC2 / PCI-aware "
        "financial operations copilot. Reference the policy gates that would apply. "
        "Be terse ? under 120 words."
    ),
    "agency": (
        "You are Veklom's governed AI control plane demo. Answer as a multi-tenant "
        "agency copilot. Reference tenant isolation, per-client budgets, and audit "
        "artifacts. Be terse ? under 120 words."
    ),
    "infrastructure": (
        "You are Veklom's governed AI control plane demo. Answer as a legacy-infrastructure "
        "ops copilot bridging SNMP / Modbus signals to governed AI decisions. Reference "
        "normalization, policy control, and auditability. Be terse ? under 120 words."
    ),
    "default": (
        "You are Veklom's governed AI control plane demo. Prove Veklom controls AI "
        "execution before it runs ? routing, memory, policy, audit, and cost. Be terse ? "
        "under 120 words."
    ),
}


# ?? Helpers ???????????????????????????????????????????????????????????????????


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "0.0.0.0"


def _ip_hash(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def _sse(event: str, data: dict) -> str:
    """Format a single Server-Sent Event frame."""
    payload = json.dumps(data, separators=(",", ":"), default=str)
    return f"event: {event}\ndata: {payload}\n\n"


def _rate_limit(ip: str) -> tuple[bool, int, int]:
    """
    Redis-backed sliding-ish counter. Returns (allowed, hits_in_window, ttl).
    Fails open on Redis outage so the demo never hard-dies in a CDN edge hiccup.
    """
    try:
        r = get_redis()
        key = f"veklom:demo:rl:{_ip_hash(ip)}"
        hits = r.incr(key)
        if hits == 1:
            r.expire(key, _DEMO_RATE_LIMIT_WINDOW_SEC)
        ttl = r.ttl(key) or _DEMO_RATE_LIMIT_WINDOW_SEC
        return hits <= _DEMO_RATE_LIMIT_MAX_HITS, int(hits), int(ttl)
    except Exception as exc:  # pragma: no cover - Redis hiccup, fail open
        logger.warning("[demo/stream] Redis unavailable for rate-limit: %s", exc)
        return True, 0, _DEMO_RATE_LIMIT_WINDOW_SEC


def _record_demo_echo(trace_id: str, prompt_preview: str, response_preview: str) -> None:
    """Ephemeral demo echo ? last turn only, 60s TTL, no tenant linkage."""
    try:
        r = get_redis()
        key = f"veklom:demo:echo:{trace_id}"
        r.setex(
            key,
            _DEMO_EPHEMERAL_TTL_SEC,
            json.dumps({"prompt": prompt_preview[:200], "response": response_preview[:400]}),
        )
    except Exception:  # pragma: no cover
        pass


def _chunk_text(text: str, size: int = 18) -> Iterable[str]:
    """Chunk a non-streaming response into visible deltas."""
    for i in range(0, len(text), size):
        yield text[i : i + size]


def _audit_hash(trace_id: str, model: str, provider: str, tokens: int) -> str:
    raw = f"{trace_id}|{model}|{provider}|{tokens}|{int(time.time())}"
    return hashlib.sha256(raw.encode()).hexdigest()


# ?? Endpoint ??????????????????????????????????????????????????????????????????


@router.get("/demo/pipeline/stream")
async def demo_pipeline_stream(
    request: Request,
    prompt: str = Query(..., min_length=1, max_length=_DEMO_PROMPT_MAX_CHARS),
    vertical: str = Query("default", regex=r"^(legal|medical|finance|agency|infrastructure|default)$"),
    force_fallback: bool = Query(False, description="Simulate Ollama outage to demo the circuit breaker path"),
):
    """
    Public SSE stream: watch a real Veklom request flow through the control plane.
    """
    trace_id = uuid.uuid4().hex[:12]
    ip = _client_ip(request)
    ip_h = _ip_hash(ip)
    t0 = time.perf_counter()

    allowed, hits, window_ttl = _rate_limit(ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Demo rate limit: {_DEMO_RATE_LIMIT_MAX_HITS}/{_DEMO_RATE_LIMIT_WINDOW_SEC}s. "
                   f"Retry in {window_ttl}s.",
            headers={"Retry-After": str(window_ttl)},
        )

    system = _VERTICAL_SYSTEM_PROMPTS.get(vertical, _VERTICAL_SYSTEM_PROMPTS["default"])
    effective_prompt = f"{system}\n\nUser: {prompt}\nAssistant:"

    def _gen():
        started = time.perf_counter()

        # 1. request_received
        yield _sse("request_received", {
            "trace_id": trace_id,
            "ip_hash": ip_h,
            "vertical": vertical,
            "prompt_len": len(prompt),
            "force_fallback": force_fallback,
            "ts_ms": int(time.time() * 1000),
        })
        time.sleep(0.08)

        # 2. zero_trust_check (demo mode: public allowlisted path)
        yield _sse("zero_trust_check", {
            "status": "passed",
            "demo_mode": True,
            "policy": "public_allowlist",
            "latency_ms": int((time.perf_counter() - started) * 1000),
        })
        time.sleep(0.06)

        # 3. rate_limit_check
        yield _sse("rate_limit_check", {
            "status": "passed",
            "hits": hits,
            "limit": _DEMO_RATE_LIMIT_MAX_HITS,
            "window_sec": _DEMO_RATE_LIMIT_WINDOW_SEC,
            "remaining": max(0, _DEMO_RATE_LIMIT_MAX_HITS - hits),
        })
        time.sleep(0.05)

        # 4. token_budget_check
        yield _sse("token_budget_check", {
            "status": "passed",
            "output_cap": _DEMO_OUTPUT_MAX_TOKENS,
            "plan": "public_demo",
            "billable": False,
        })
        time.sleep(0.05)

        # 5. circuit_breaker_check
        cb = cb_status()
        yield _sse("circuit_breaker_check", {
            "state": cb.get("state", "closed"),
            "failures": cb.get("failures", 0),
            "threshold": cb.get("threshold"),
            "forced": force_fallback,
        })
        time.sleep(0.05)

        # 6/7. provider selection + attempt
        provider = "ollama"
        result: Optional[dict] = None
        used_groq = force_fallback or (cb_get_state().value == "open")

        if not used_groq:
            yield _sse("provider_selected", {
                "provider": "ollama",
                "model": settings.llm_model_default,
                "reason": "circuit_closed",
                "sovereign": True,
            })
            time.sleep(0.05)
            yield _sse("ollama_attempt", {
                "model": settings.llm_model_default,
                "base_url": settings.llm_base_url,
                "stream": True,
            })

            try:
                ollama = OllamaClient()
                sdk = ollama._client  # direct stream iterator
                stream = sdk.generate(
                    model=settings.llm_model_default,
                    prompt=effective_prompt,
                    stream=True,
                    options={"num_predict": _DEMO_OUTPUT_MAX_TOKENS, "temperature": 0.5},
                )
                # 8. memory check (demo ephemeral)
                yield _sse("redis_memory_check", {
                    "demo_ephemeral": True,
                    "ttl_sec": _DEMO_EPHEMERAL_TTL_SEC,
                    "tenant_scope": "public_demo",
                })

                acc = []
                total_tokens = 0
                for chunk in stream:
                    text = getattr(chunk, "response", "") or ""
                    if text:
                        acc.append(text)
                        yield _sse("token_delta", {"delta": text, "provider": "ollama"})
                    if getattr(chunk, "done", False):
                        total_tokens = (chunk.prompt_eval_count or 0) + (chunk.eval_count or 0)
                response_text = "".join(acc).strip() or "(no content)"
                result = {
                    "response": response_text,
                    "model": settings.llm_model_default,
                    "total_tokens": total_tokens or max(1, len(response_text) // 4),
                    "prompt_tokens": 0,
                    "completion_tokens": total_tokens or max(1, len(response_text) // 4),
                }
            except OllamaError as exc:
                # graceful pivot to Groq
                yield _sse("ollama_unavailable", {
                    "reason": str(exc)[:200],
                    "simulated": False,
                })
                time.sleep(0.05)
                yield _sse("circuit_breaker_opened", {
                    "simulated": False,
                    "note": "Demo observer only ? production CB is per-tenant.",
                })
                used_groq = True
                provider = "groq"
        else:
            # Forced fallback ? theatrically show the circuit breaker path.
            yield _sse("provider_selected", {
                "provider": "ollama",
                "model": settings.llm_model_default,
                "reason": "circuit_closed",
                "sovereign": True,
            })
            time.sleep(0.1)
            yield _sse("ollama_unavailable", {
                "reason": "Simulated outage (force_fallback=true)",
                "simulated": True,
            })
            time.sleep(0.08)
            yield _sse("circuit_breaker_opened", {
                "simulated": True,
                "note": "Real production CB was NOT toggled.",
            })
            provider = "groq"

        # Groq fallback path
        if used_groq or result is None:
            yield _sse("provider_selected", {
                "provider": "groq",
                "model": settings.groq_model,
                "reason": "fallback",
                "sovereign": False,
            })
            time.sleep(0.05)
            yield _sse("redis_memory_check", {
                "demo_ephemeral": True,
                "ttl_sec": _DEMO_EPHEMERAL_TTL_SEC,
                "tenant_scope": "public_demo",
            })

            if not settings.groq_api_key:
                yield _sse("error", {
                    "stage": "groq_fallback",
                    "message": "Groq fallback not configured on this deployment.",
                })
                # still emit a synthetic completion so the UI locks in a final state
                synthetic = (
                    "Veklom would route this request to Groq here. In this deployment the "
                    "GROQ_API_KEY is not set, so the fallback leg is observable but not "
                    "executed. On production the circuit breaker would complete the call "
                    "and record the failover in the audit trail."
                )
                for delta in _chunk_text(synthetic, 22):
                    time.sleep(0.04)
                    yield _sse("token_delta", {"delta": delta, "provider": "groq_simulated"})
                result = {
                    "response": synthetic,
                    "model": f"groq/{settings.groq_model}",
                    "total_tokens": len(synthetic) // 4,
                    "prompt_tokens": 0,
                    "completion_tokens": len(synthetic) // 4,
                }
                provider = "groq_simulated"
            else:
                try:
                    groq_result = call_groq(
                        prompt=effective_prompt,
                        max_tokens=_DEMO_OUTPUT_MAX_TOKENS,
                        temperature=0.5,
                    )
                    text = groq_result["response"].strip() or "(no content)"
                    for delta in _chunk_text(text, 22):
                        time.sleep(0.03)
                        yield _sse("token_delta", {"delta": delta, "provider": "groq"})
                    result = {
                        "response": text,
                        "model": groq_result["model"],
                        "total_tokens": groq_result["total_tokens"],
                        "prompt_tokens": groq_result["prompt_tokens"],
                        "completion_tokens": groq_result["completion_tokens"],
                    }
                    provider = "groq"
                except GroqFallbackError as exc:
                    yield _sse("error", {
                        "stage": "groq_fallback",
                        "message": str(exc)[:300],
                    })
                    result = {
                        "response": f"Groq fallback failed: {exc}",
                        "model": f"groq/{settings.groq_model}",
                        "total_tokens": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                    }

        latency_ms = int((time.perf_counter() - started) * 1000)

        # 9. response_complete
        yield _sse("response_complete", {
            "provider": provider,
            "model": result["model"],
            "prompt_tokens": result.get("prompt_tokens", 0),
            "completion_tokens": result.get("completion_tokens", 0),
            "total_tokens": result.get("total_tokens", 0),
            "latency_ms": latency_ms,
            "response_preview": result["response"][:240],
        })
        time.sleep(0.04)

        # 10. audit_written (demo-safe, in-memory hash ? not persisted to audit_logs)
        audit_id = _audit_hash(trace_id, result["model"], provider, result.get("total_tokens", 0))
        yield _sse("audit_written", {
            "trace_id": trace_id,
            "audit_hash": audit_id,
            "store": "demo_ephemeral",
            "fields": ["trace_id", "provider", "model", "tokens", "latency_ms", "policy_result"],
        })
        time.sleep(0.04)

        # 11. cost_recorded
        yield _sse("cost_recorded", {
            "billable": False,
            "public_demo": True,
            "credits_charged": 0,
            "customer_route_cost_credits": None,
            "note": "Production requests are metered per-tenant in USD + credits.",
        })

        # ephemeral echo (safe, no PII, short TTL)
        _record_demo_echo(trace_id, prompt, result["response"])

        # 12. done
        yield _sse("done", {
            "trace_id": trace_id,
            "total_latency_ms": int((time.perf_counter() - started) * 1000),
        })

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",  # disable nginx buffering
        "Connection": "keep-alive",
    }
    return StreamingResponse(_gen(), media_type="text/event-stream", headers=headers)


@router.get("/demo/pipeline/health")
async def demo_pipeline_health():
    """Lightweight health probe for the demo surface (landing page polls this)."""
    cb = cb_status()
    try:
        ollama = OllamaClient()
        llm_ok = ollama.health_check()
    except Exception:
        llm_ok = False
    return {
        "ok": True,
        "llm_ok": llm_ok,
        "groq_fallback_enabled": bool(settings.groq_api_key and settings.llm_fallback == "groq"),
        "circuit_breaker": cb,
        "limits": {
            "prompt_max_chars": _DEMO_PROMPT_MAX_CHARS,
            "output_max_tokens": _DEMO_OUTPUT_MAX_TOKENS,
            "rate_limit_per_minute": _DEMO_RATE_LIMIT_MAX_HITS,
        },
    }
