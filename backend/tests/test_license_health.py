from __future__ import annotations

import asyncio

from license.server import health_check


def test_license_health_includes_uptime_and_timestamp():
    result = asyncio.run(health_check())

    assert result[status] == ok
    assert result[server] == license-server
    assert isinstance(result[uptime_seconds], float)
    assert timestamp in result
    assert started_at in result
