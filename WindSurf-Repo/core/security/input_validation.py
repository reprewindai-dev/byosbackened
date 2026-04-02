"""Input validation and sanitization to prevent injection attacks."""

import re
import html
from typing import Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class InputValidator:
    """Validate and sanitize user input."""

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|SCRIPT)\b)",
        r"(--|#|/\*|\*/)",
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
        r"(;.*--|;.*#)",
    ]

    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",  # onclick=, onerror=, etc.
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
        r"<link[^>]*>",
        r"<meta[^>]*>",
        r"<style[^>]*>.*?</style>",
        r"expression\s*\(",
        r"vbscript:",
        r"data:text/html",
    ]

    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$]",
        r"\b(cat|ls|pwd|whoami|id|uname|ps|kill|rm|mv|cp|chmod|chown)\b",
        r"(\$\(|`|&&|\|\|)",
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"\.\.%2F",
        r"\.\.%5C",
        r"\.\.%252F",
        r"\.\.%255C",
    ]

    @classmethod
    def validate_string(
        cls,
        value: Any,
        max_length: Optional[int] = None,
        allow_html: bool = False,
        allow_sql: bool = False,
        allow_xss: bool = False,
        allow_command_injection: bool = False,
        allow_path_traversal: bool = False,
    ) -> tuple[bool, Optional[str]]:
        """
        Validate string input.

        Returns:
            (is_valid, error_message)
        """
        if not isinstance(value, str):
            return False, "Input must be a string"

        # Check length
        if max_length and len(value) > max_length:
            return False, f"Input exceeds maximum length of {max_length}"

        # Check SQL injection
        if not allow_sql:
            for pattern in cls.SQL_INJECTION_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):
                    logger.warning(f"SQL injection attempt detected: {value[:50]}")
                    return False, "Invalid input: potential SQL injection detected"

        # Check XSS
        if not allow_xss:
            for pattern in cls.XSS_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):
                    logger.warning(f"XSS attempt detected: {value[:50]}")
                    return False, "Invalid input: potential XSS detected"

        # Check command injection
        if not allow_command_injection:
            for pattern in cls.COMMAND_INJECTION_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):
                    logger.warning(f"Command injection attempt detected: {value[:50]}")
                    return False, "Invalid input: potential command injection detected"

        # Check path traversal
        if not allow_path_traversal:
            for pattern in cls.PATH_TRAVERSAL_PATTERNS:
                if pattern in value:
                    logger.warning(f"Path traversal attempt detected: {value[:50]}")
                    return False, "Invalid input: potential path traversal detected"

        return True, None

    @classmethod
    def sanitize_string(
        cls,
        value: str,
        escape_html: bool = True,
        strip_tags: bool = False,
    ) -> str:
        """Sanitize string input."""
        if not isinstance(value, str):
            return str(value)

        # Remove null bytes
        value = value.replace("\x00", "")

        # Strip HTML tags if requested
        if strip_tags:
            value = re.sub(r"<[^>]+>", "", value)

        # Escape HTML entities
        if escape_html:
            value = html.escape(value, quote=True)

        return value

    @classmethod
    def validate_email(cls, email: str) -> tuple[bool, Optional[str]]:
        """Validate email address."""
        if not email:
            return False, "Email is required"

        # Basic email regex
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            return False, "Invalid email format"

        # Check length
        if len(email) > 254:  # RFC 5321 limit
            return False, "Email address too long"

        # Check for injection attempts
        is_valid, error = cls.validate_string(
            email,
            allow_sql=False,
            allow_xss=False,
            allow_command_injection=False,
        )
        if not is_valid:
            return False, error

        return True, None

    @classmethod
    def validate_url(
        cls, url: str, allowed_schemes: List[str] = None
    ) -> tuple[bool, Optional[str]]:
        """Validate URL."""
        if not url:
            return False, "URL is required"

        if allowed_schemes is None:
            allowed_schemes = ["http", "https"]

        # Check for valid scheme
        if not any(url.startswith(f"{scheme}://") for scheme in allowed_schemes):
            return False, f"URL must start with one of: {', '.join(allowed_schemes)}"

        # Check for injection attempts
        is_valid, error = cls.validate_string(
            url,
            allow_sql=False,
            allow_xss=False,
            allow_command_injection=False,
            allow_path_traversal=False,
        )
        if not is_valid:
            return False, error

        return True, None

    @classmethod
    def validate_password_strength(cls, password: str) -> tuple[bool, Optional[str]]:
        """Validate password strength."""
        if not password:
            return False, "Password is required"

        # Minimum length
        if len(password) < 12:
            return False, "Password must be at least 12 characters long"

        # Maximum length
        if len(password) > 128:
            return False, "Password must be less than 128 characters"

        # Check for uppercase
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"

        # Check for lowercase
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"

        # Check for digit
        if not re.search(r"\d", password):
            return False, "Password must contain at least one digit"

        # Check for special character
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", password):
            return False, "Password must contain at least one special character"

        # Check for common passwords
        common_passwords = [
            "password",
            "123456",
            "password123",
            "admin",
            "qwerty",
            "letmein",
            "welcome",
            "monkey",
            "1234567890",
            "abc123",
        ]
        if password.lower() in common_passwords:
            return False, "Password is too common. Please choose a stronger password"

        return True, None
