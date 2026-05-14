"""Veklom SDK exceptions."""


class VeklomError(Exception):
    """Base exception for all Veklom SDK errors."""


class AuthError(VeklomError):
    """Raised on 401 / 403 responses."""


class RateLimitError(VeklomError):
    """Raised on 429 responses."""


class BudgetExceededError(VeklomError):
    """Raised when workspace budget cap is hit."""


class ModelUnavailableError(VeklomError):
    """Raised when the requested model is offline and no fallback is available."""
