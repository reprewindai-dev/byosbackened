from apps.api.routers import demo_pipeline


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.ttls = {}

    def incr(self, key):
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def expire(self, key, ttl):
        self.ttls[key] = ttl

    def ttl(self, key):
        return self.ttls.get(key, demo_pipeline._DEMO_SMART_GROQ_QUOTA_WINDOW_SEC)


def test_smart_groq_quota_limits_after_three_hits(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(demo_pipeline, "get_redis", lambda: redis)

    assert demo_pipeline._smart_groq_quota("203.0.113.10") == (True, 1, 3600)
    assert demo_pipeline._smart_groq_quota("203.0.113.10") == (True, 2, 3600)
    assert demo_pipeline._smart_groq_quota("203.0.113.10") == (True, 3, 3600)
    assert demo_pipeline._smart_groq_quota("203.0.113.10") == (False, 4, 3600)


def test_smart_groq_quota_uses_ip_hash_key(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(demo_pipeline, "get_redis", lambda: redis)

    demo_pipeline._smart_groq_quota("203.0.113.11")

    assert list(redis.values) == [
        f"veklom:demo:smart_groq:{demo_pipeline._ip_hash('203.0.113.11')}"
    ]


def test_smart_groq_quota_fails_closed_when_redis_unavailable(monkeypatch):
    def broken_redis():
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr(demo_pipeline, "get_redis", broken_redis)

    allowed, hits, ttl = demo_pipeline._smart_groq_quota("203.0.113.12")

    assert allowed is False
    assert hits == demo_pipeline._DEMO_SMART_GROQ_QUOTA_MAX_HITS + 1
    assert ttl == demo_pipeline._DEMO_SMART_GROQ_QUOTA_WINDOW_SEC


def test_synthetic_governed_response_is_safe_and_deterministic():
    reason = "The public smart-model quota for this IP is temporarily exhausted."

    first = demo_pipeline._synthetic_governed_response(reason)
    second = demo_pipeline._synthetic_governed_response(reason)

    assert first == second
    assert "deterministic response" in first
    assert "secrets" in first
    assert "Groq" not in first
