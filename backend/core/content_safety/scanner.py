from typing import Any

from apps.api.routers.content_safety import _scan_content


def scan_text(text: str) -> dict[str, Any]:
    """Scan text for prohibited/adult content. Returns {flagged, flags, category}."""
    result = _scan_content(
        content_hash=None,
        content_type="text/plain",
        filename=text,
        tags=None,
    )
    flagged = not result.allowed or bool(result.flags)
    return {
        "flagged": flagged,
        "flags": result.flags,
        "category": result.category,
    }
