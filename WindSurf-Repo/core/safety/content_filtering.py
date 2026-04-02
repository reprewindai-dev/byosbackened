"""Content filtering."""

from typing import List, Dict
import re
import logging

logger = logging.getLogger(__name__)


class ContentFilter:
    """Filter harmful content."""

    # Patterns for harmful content (basic - can be enhanced with ML models)
    HARMFUL_PATTERNS = [
        # Hate speech patterns (basic)
        re.compile(r"\b(kill|murder|violence)\b", re.IGNORECASE),
        # Spam patterns
        re.compile(r"\b(buy now|click here|limited time)\b", re.IGNORECASE),
    ]

    def filter_content(self, text: str) -> Dict[str, any]:
        """
        Filter harmful content.

        Returns:
        - is_safe: bool
        - flags: List[str] (types of harmful content detected)
        - filtered_text: str (text with harmful content removed)
        """
        flags = []
        filtered_text = text

        for pattern in self.HARMFUL_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                flags.append("harmful_content")
                # Remove matches (basic filtering)
                filtered_text = pattern.sub("[FILTERED]", filtered_text)

        is_safe = len(flags) == 0

        if not is_safe:
            logger.warning(f"Content filtered: flags={flags}, text_preview={text[:100]}")

        return {
            "is_safe": is_safe,
            "flags": flags,
            "filtered_text": filtered_text,
        }
