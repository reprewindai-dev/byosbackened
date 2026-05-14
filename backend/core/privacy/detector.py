from core.privacy.pii_detection import detect_pii as _detect_pii


def detect_pii(text: str) -> dict[str, object]:
    """Returns {types: [...], count: int}."""
    detections = _detect_pii(text)
    types = sorted({item["type"] for item in detections if item.get("type")})
    return {
        "types": types,
        "count": len(detections),
    }
