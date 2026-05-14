from core.services.qstash_dispatch import job_url, workflow_url


def test_qstash_job_url_joins_base_and_path(monkeypatch):
    from core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "qstash_callback_base_url", "https://api.veklom.com")

    assert job_url() == "https://api.veklom.com/api/v1/webhooks/qstash/uacp-job"


def test_qstash_workflow_url_uses_registered_route(monkeypatch):
    from core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "qstash_callback_base_url", "https://api.veklom.com")
    monkeypatch.setattr(settings, "upstash_workflow_url", "")

    assert workflow_url() == "https://api.veklom.com/api/v1/workflows/uacp-maintenance"
