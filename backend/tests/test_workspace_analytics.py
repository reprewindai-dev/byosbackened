from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace

from apps.api.routers import workspace


def test_workspace_analytics_defaults_to_last_30_days(monkeypatch):
    captured = {}

    def fake_fetch_workspace_request_metrics(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(workspace, "fetch_workspace_request_metrics", fake_fetch_workspace_request_metrics)

    result = asyncio.run(
        workspace.workspace_analytics_requests(
            current_user=SimpleNamespace(workspace_id="workspace-1"),
            db=SimpleNamespace(),
            start_date=None,
            end_date=None,
            include_rows=True,
        )
    )

    assert result == {"ok": True}
    assert captured["workspace_id"] == "workspace-1"
    assert isinstance(captured["start_date"], datetime)
    assert isinstance(captured["end_date"], datetime)
    assert timedelta(days=29, hours=23) <= captured["end_date"] - captured["start_date"] <= timedelta(days=30, minutes=1)
    assert captured["include_rows"] is True

