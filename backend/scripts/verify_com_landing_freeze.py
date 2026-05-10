"""Fail if the frozen veklom.com landing page changes unexpectedly."""

from __future__ import annotations

import hashlib
from pathlib import Path


EXPECTED_SHA256 = "42DDCC746BD6DFDCC2225693C404DEFECE5289726355D9E91CD184A4E0834E18".lower()


def frozen_bytes(path: Path) -> bytes:
    """Keep the freeze stable across Windows checkouts and Linux CI."""
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    landing = repo_root / "backend" / "landing" / "index.html"
    actual = hashlib.sha256(frozen_bytes(landing)).hexdigest()
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
