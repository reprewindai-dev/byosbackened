from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.services.workspace_gateway import record_request_log
from db.models import VeklomRun, Workspace, WorkspaceRequestLog
from db.session import Base


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}
        self.expirations: dict[str, int] = {}

    def setex(self, key: str, seconds: int, value: str) -> None:
        self.values[key] = value
        self.expirations[key] = seconds

    def lpush(self, key: str, value: str) -> None:
        self.lists.setdefault(key, []).insert(0, value)

    def ltrim(self, key: str, start: int, end: int) -> None:
        self.lists[key] = self.lists.get(key, [])[start : end + 1]

    def expire(self, key: str, seconds: int) -> None:
        self.expirations[key] = seconds


def test_record_request_log_writes_canonical_veklom_run(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr("core.redis_pool.get_redis", lambda: fake_redis)

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as db:
        workspace = Workspace(id="workspace-v5", name="V5 Workspace", slug="workspace-v5")
        db.add(workspace)
        db.commit()

        request_log = record_request_log(
            db,
            workspace_id=workspace.id,
            request_kind="ai.complete",
            request_path="/api/v1/ai/complete",
            model="qwen2.5:3b",
            provider="ollama",
            status="success",
            prompt_preview="Compile this into a governed run.",
            response_preview="Run admitted.",
            request_json={"prompt": "Compile this into a governed run."},
            response_json={"response_text": "Run admitted.", "fallback_triggered": False},
            tokens_in=12,
            tokens_out=6,
            latency_ms=88,
            cost_usd=Decimal("0.000180"),
            source_table="ai_audit_logs",
            source_id="audit-v5",
            user_id="user-v5",
        )

        run = db.query(VeklomRun).one()
        assert db.query(WorkspaceRequestLog).count() == 1
        assert run.workspace_id == workspace.id
        assert run.tenant_id == workspace.id
        assert run.actor_id == "user-v5"
        assert run.request_log_id == request_log.id
        assert run.source_table == "ai_audit_logs"
        assert run.source_id == "audit-v5"
        assert run.status == "SEALED"
        assert run.governance_decision == "ALLOW"
        assert run.input_hash
        assert run.output_hash
        assert run.genome_hash
        assert run.decision_frame_hash
        assert f"uacp:v5:run:{run.run_id}" in fake_redis.values
        assert "uacp:v5:workspace:workspace-v5:latest_run" in fake_redis.values
        assert fake_redis.lists["uacp:v5:event-stream"]
