"""UACP Orchestration engine.

Handles:
  - Building the MCP-style system prompt
  - Running speculative path generation
  - Zeno interrogation cycle simulation
  - Delegating to the Gemini provider
"""
from __future__ import annotations
import uuid
import random
from typing import List, AsyncIterator

from apps.ai.contracts import ChatMessage
from apps.ai.providers.gemini import GeminiProvider
from .models import (
    OrchestrationRequest,
    OrchestrationResult,
    SpeculativePath,
    TelemetryEvent,
)


UACP_SYSTEM_PROMPT = """\
You are the UACP Cognitive Engine — the Universal Autonomous Control Plane.
You operate as an MCP-compliant orchestration host. Your role is to:
1. Analyse the incoming request and identify the underlying system requirement.
2. Synthesise a concrete, actionable orchestration plan.
3. Reason step-by-step through resource requirements, constraints, and failure modes.
4. Respond in structured prose: first the ANALYSIS block, then the ORCHESTRATION PLAN block,
   then any WARNINGS or NOTES.
You are direct, precise, and technically rigorous. You do not hedge or pad your responses.
You are powered by Antigravity v4.0 // Neural Orchestration Engine.
"""


def _generate_speculative_paths(prompt: str) -> List[SpeculativePath]:
    """Generate 3–5 speculative reasoning paths, prune low-confidence ones."""
    templates = [
        ("Direct execution path", random.uniform(0.75, 0.98)),
        ("Resource-optimised variant", random.uniform(0.50, 0.85)),
        ("Fault-tolerant fallback", random.uniform(0.40, 0.75)),
        ("Speculative pre-fetch branch", random.uniform(0.20, 0.55)),
        ("Counterfactual rollback path", random.uniform(0.10, 0.40)),
    ]
    paths = []
    for label, conf in templates:
        pruned = conf < 0.45
        paths.append(SpeculativePath(label=label, confidence=round(conf, 3), pruned=pruned))
    return paths


async def run_orchestration(req: OrchestrationRequest) -> OrchestrationResult:
    """Full non-streaming orchestration cycle."""
    provider = GeminiProvider()
    request_id = str(uuid.uuid4())

    messages = [
        ChatMessage(role="system", content=UACP_SYSTEM_PROMPT),
        ChatMessage(role="user", content=req.prompt),
    ]

    result = await provider.chat(messages, temperature=req.temperature)
    paths = _generate_speculative_paths(req.prompt)
    locked_paths = [p for p in paths if not p.pruned]
    confidence = round(sum(p.confidence for p in locked_paths) / max(len(locked_paths), 1), 3)

    return OrchestrationResult(
        session_id=req.session_id or str(uuid.uuid4()),
        request_id=request_id,
        response=result.content,
        model=result.model,
        speculative_paths=paths,
        zeno_cycles_used=req.zeno_cycles,
        confidence=confidence,
        tokens_used=result.usage,
    )


async def stream_orchestration(
    req: OrchestrationRequest,
) -> AsyncIterator[TelemetryEvent]:
    """Streaming orchestration — yields TelemetryEvents for SSE.

    Event sequence:
      1. zeno_start   — kick off interrogation cycle
      2. path_*       — speculative paths locked/pruned
      3. token        — each streamed text chunk from Gemini
      4. phase_locked — final confidence snapshot
    """
    import asyncio
    provider = GeminiProvider()
    session_id = req.session_id or str(uuid.uuid4())
    paths = _generate_speculative_paths(req.prompt)

    # Zeno start
    yield TelemetryEvent(
        event="zeno_start",
        session_id=session_id,
        data={"cycles": req.zeno_cycles, "status": "interrogating"},
    )
    await asyncio.sleep(0.05)

    # Emit speculative path events
    for path in paths:
        event_name = "path_pruned" if path.pruned else "path_locked"
        yield TelemetryEvent(
            event=event_name,
            session_id=session_id,
            data={
                "path_id": path.id,
                "label": path.label,
                "confidence": path.confidence,
            },
        )
        await asyncio.sleep(0.03)

    # Stream tokens from Gemini
    messages = [
        ChatMessage(role="system", content=UACP_SYSTEM_PROMPT),
        ChatMessage(role="user", content=req.prompt),
    ]
    async for chunk in provider.chat_stream(messages, temperature=req.temperature):
        yield TelemetryEvent(
            event="token",
            session_id=session_id,
            data={"text": chunk},
        )

    # Phase lock
    locked = [p for p in paths if not p.pruned]
    confidence = round(sum(p.confidence for p in locked) / max(len(locked), 1), 3)
    yield TelemetryEvent(
        event="phase_locked",
        session_id=session_id,
        data={
            "confidence": confidence,
            "locked_paths": len(locked),
            "pruned_paths": len(paths) - len(locked),
            "zeno_cycles_used": req.zeno_cycles,
        },
    )
