"""
Redis-backed conversation memory — per-tenant, per-conversation.

Key format:  tenant:{tenant_id}:conv:{conv_id}
Structure:   Redis LIST of JSON-serialised message dicts, newest at tail.
TTL:         settings.memory_ttl_seconds (default 24h), refreshed on every write.

Usage:
    mem = ConversationMemory(tenant_id="workspace-001", conversation_id="sess-abc")
    mem.add("user", "What is quantum computing?")
    mem.add("assistant", "Quantum computing uses qubits...")
    ctx = mem.build_context_prompt()   # injected before the new prompt
    history = mem.get_messages()       # list of {role, content}
"""
import json
import logging
from typing import Optional

from core.redis_pool import get_redis
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _redis():
    """Get Redis from shared connection pool."""
    return get_redis()


class ConversationMemory:
    def __init__(self, tenant_id: str, conversation_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self.conversation_id = conversation_id or "default"
        self._key = f"tenant:{tenant_id}:conv:{self.conversation_id}"
        self._ttl = settings.memory_ttl_seconds
        self._max = settings.memory_max_messages

    # ── Write ─────────────────────────────────────────────────────────────────

    def add(self, role: str, content: str) -> None:
        """Append a message and refresh TTL. Trims to max_messages."""
        try:
            r = _redis()
            msg = json.dumps({"role": role, "content": content})
            pipe = r.pipeline()
            pipe.rpush(self._key, msg)
            pipe.ltrim(self._key, -self._max, -1)   # keep newest N
            pipe.expire(self._key, self._ttl)
            pipe.execute()
        except Exception as e:
            logger.warning("[Memory] Could not save message: %s", e)

    def clear(self) -> None:
        """Wipe this conversation's history."""
        try:
            _redis().delete(self._key)
        except Exception as e:
            logger.warning("[Memory] Could not clear conversation: %s", e)

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_messages(self) -> list[dict]:
        """Return all stored messages as [{role, content}, ...]."""
        try:
            raw = _redis().lrange(self._key, 0, -1)
            return [json.loads(m) for m in raw]
        except Exception as e:
            logger.warning("[Memory] Could not read messages: %s", e)
            return []

    def build_context_prompt(self) -> str:
        """
        Format conversation history as a text block to prepend to new prompts.
        Empty string if no history exists.
        """
        messages = self.get_messages()
        if not messages:
            return ""

        lines = ["[Conversation history]"]
        for m in messages:
            role = m.get("role", "user").capitalize()
            content = m.get("content", "").strip()
            lines.append(f"{role}: {content}")
        lines.append("[End history]\n")
        return "\n".join(lines)

    def message_count(self) -> int:
        """Number of messages stored."""
        try:
            return _redis().llen(self._key)
        except Exception:
            return 0


def get_memory(tenant_id: str, conversation_id: Optional[str] = None) -> ConversationMemory:
    """Factory — returns a ConversationMemory instance for the given tenant/conversation."""
    return ConversationMemory(tenant_id=tenant_id, conversation_id=conversation_id)
