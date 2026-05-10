"""Fail if the frozen veklom.com landing page changes unexpectedly."""

from __future__ import annotations

import hashlib
from pathlib import Path


EXPECTED_SHA256 = "5C062A6CAD054253C613FE73E2D16EB59A9FECA5FF4FABBDDAE5752A382357F1".lower()


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    landing = repo_root / "backend" / "landing" / "index.html"
    actual = hashlib.sha256(landing.read_bytes()).hexdigest()
    if actual != EXPECTED_SHA256:
        raise SystemExit(
            "veklom.com landing page freeze violation: "
            f"expected {EXPECTED_SHA256}, got {actual}. "
            "If this is an intentional .com landing change, update "
            "backend/landing/COM_FREEZE_LOCK.md and this script in the same commit."
        )
    print(f"veklom.com landing freeze verified: {actual}")


if __name__ == "__main__":
    main()
