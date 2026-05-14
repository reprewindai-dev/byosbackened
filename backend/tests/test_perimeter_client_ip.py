from __future__ import annotations

from starlette.requests import Request

from core.security import client_ip


def _request(peer: str, headers: dict[str, str] | None = None) -> Request:
    raw_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/auth/login",
        "headers": raw_headers,
        "client": (peer, 44321),
        "server": ("api.veklom.com", 443),
        "scheme": "https",
    }
    return Request(scope)


def test_direct_clients_cannot_spoof_x_forwarded_for():
    request = _request(
        "203.0.113.10",
        {
            "X-Forwarded-For": "198.51.100.99",
            "X-Real-IP": "198.51.100.88",
            "CF-Connecting-IP": "198.51.100.77",
        },
    )

    assert client_ip.get_client_ip(request) == "203.0.113.10"


def test_trusted_proxy_can_supply_cloudflare_client_ip():
    request = _request("172.18.0.2", {"CF-Connecting-IP": "198.51.100.77"})

    assert client_ip.get_client_ip(request) == "198.51.100.77"


def test_trusted_proxy_falls_back_to_x_real_ip():
    request = _request("10.0.0.5", {"X-Real-IP": "198.51.100.88"})

    assert client_ip.get_client_ip(request) == "198.51.100.88"


def test_trusted_proxy_uses_first_valid_forwarded_ip():
    request = _request("127.0.0.1", {"X-Forwarded-For": "bad-value, 198.51.100.99"})

    assert client_ip.get_client_ip(request) == "198.51.100.99"


def test_invalid_forwarding_headers_fall_back_to_peer():
    request = _request("192.168.1.10", {"CF-Connecting-IP": "not-an-ip"})

    assert client_ip.get_client_ip(request) == "192.168.1.10"
