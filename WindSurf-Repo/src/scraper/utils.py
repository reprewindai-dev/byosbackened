"""Utility functions for scrapers."""

import re
from typing import Optional


def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from various URL formats."""
    # PornHub viewkey
    match = re.search(r"viewkey=([a-zA-Z0-9]+)", url)
    if match:
        return match.group(1)

    # Direct ID in path
    match = re.search(r"/view_video\.php\?viewkey=([a-zA-Z0-9]+)", url)
    if match:
        return match.group(1)

    # Hash-based ID
    match = re.search(r"/([a-zA-Z0-9]{10,})", url)
    if match:
        return match.group(1)

    return None


def clean_title(title: str) -> str:
    """Clean and normalize video title."""
    if not title:
        return ""

    # Remove extra whitespace
    title = " ".join(title.split())

    # Remove HTML entities
    title = title.replace("&amp;", "&")
    title = title.replace("&lt;", "<")
    title = title.replace("&gt;", ">")
    title = title.replace("&quot;", '"')
    title = title.replace("&#39;", "'")

    return title.strip()


def parse_duration(duration_str: str) -> int:
    """Parse duration string to seconds."""
    if not duration_str:
        return 0

    # Format: "HH:MM:SS" or "MM:SS"
    parts = duration_str.split(":")

    if len(parts) == 3:
        hours, minutes, seconds = map(int, parts)
        return hours * 3600 + minutes * 60 + seconds
    elif len(parts) == 2:
        minutes, seconds = map(int, parts)
        return minutes * 60 + seconds
    elif len(parts) == 1:
        return int(parts[0])

    return 0


def normalize_category(category: str) -> str:
    """Normalize category name to slug."""
    if not category:
        return ""

    # Convert to lowercase
    category = category.lower()

    # Replace spaces and special chars with hyphens
    category = re.sub(r"[^\w\s-]", "", category)
    category = re.sub(r"[-\s]+", "-", category)

    return category.strip("-")
