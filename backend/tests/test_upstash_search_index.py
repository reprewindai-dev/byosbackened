from datetime import datetime
from types import SimpleNamespace

from core.services.upstash_search_index import build_veklom_run_document


def test_build_veklom_run_document_contains_proof_hashes():
    run = SimpleNamespace(
        run_id="run_123",
        workspace_id="ws_1",
        tenant_id="ws_1",
        actor_id="user_1",
        status="SEALED",
        governance_decision="ALLOW",
        risk_tier="LOW",
        raw_intent="Generate governed artifact",
        decision_frame_hash="decision_hash",
        created_at=datetime(2026, 5, 12, 12, 0, 0),
    )
    row = SimpleNamespace(
        id="request_1",
        provider="groq",
        model="llama",
        request_kind="ai.complete",
        request_path="/api/v1/ai/complete",
        source_table="ai_audit_logs",
        source_id="audit_1",
        prompt_preview="prompt",
        response_preview="artifact",
        error_message=None,
        created_at=datetime(2026, 5, 12, 12, 0, 0),
    )

    document = build_veklom_run_document(
        run=run,
        row=row,
        input_hash="input_hash",
        output_hash="output_hash",
        genome_hash="genome_hash",
    )

    assert document["id"] == "veklom-run-run_123"
    assert document["content"]["kind"] == "veklom_run"
    assert document["metadata"]["run_id"] == "run_123"
    assert document["metadata"]["input_hash"] == "input_hash"
    assert document["metadata"]["output_hash"] == "output_hash"
    assert document["metadata"]["genome_hash"] == "genome_hash"
    assert document["metadata"]["decision_frame_hash"] == "decision_hash"
