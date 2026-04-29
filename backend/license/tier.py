"""Shared license tier definitions."""
from __future__ import annotations

import enum


class LicenseTier(str, enum.Enum):
    STARTER = "starter"
    PRO = "pro"
    SOVEREIGN = "sovereign"
    ENTERPRISE = "enterprise"
