"""Trusted proxy client IP resolution for perimeter-aware security controls."""

from __future__ import annotations

import ipaddress
import os
from functools import lru_cache
from typing import Iterable

from fastapi import Request


DEFAULT_TRUSTED_PROXY_CIDRS = (
    "127.0.0.0/8",
    "::1/128",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
)


def _split_csv(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


@lru_cache(maxsize=1)
def _trusted_proxy_networks() -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    configured = _split_csv(os.getenv("TRUSTED_PROXY_CIDRS"))
    cidrs = configured or list(DEFAULT_TRUSTED_PROXY_CIDRS)
    networks = []
    for cidr in cidrs:
        try:
            networks.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError:
            continue
    return tuple(networks)


@lru_cache(maxsize=1)
def _trusted_proxy_ips() -> frozenset[str]:
    return frozenset(_split_csv(os.getenv("TRUSTED_PROXY_IPS")))


def _valid_ip(value: str | None) -> str | None:
    if not value:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        return None
    return candidate


def _peer_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def is_trusted_proxy_ip(ip: str) -> bool:
    """Return whether an immediate peer is trusted to set forwarding headers."""
    parsed = _valid_ip(ip)
    if not parsed:
        return False
    if parsed in _trusted_proxy_ips():
        return True
    address = ipaddress.ip_address(parsed)
    return any(address in network for network in _trusted_proxy_networks())


def _first_valid_ip(values: Iterable[str]) -> str | None:
    for value in values:
        parsed = _valid_ip(value)
        if parsed:
            return parsed
    return None


def get_client_ip(request: Request) -> str:
    """Resolve the client IP without trusting spoofable headers from direct clients.

    Only immediate trusted proxies may provide Cloudflare, X-Real-IP, or
    X-Forwarded-For client attribution. Direct internet callers are always
    attributed to the socket peer.
    """
    peer = _peer_ip(request)
    if not is_trusted_proxy_ip(peer):
        return peer

    cf_ip = _valid_ip(request.headers.get("CF-Connecting-IP"))
    if cf_ip:
        return cf_ip

    real_ip = _valid_ip(request.headers.get("X-Real-IP"))
    if real_ip:
        return real_ip

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        forwarded_ip = _first_valid_ip(forwarded.split(","))
        if forwarded_ip:
            return forwarded_ip

    return peer
