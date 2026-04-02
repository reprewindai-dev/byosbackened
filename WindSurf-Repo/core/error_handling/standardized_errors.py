"""
Standardized Error Handling System
==================================

Comprehensive error handling with standardized responses,
recovery mechanisms, and detailed error reporting.
"""

import logging
import traceback
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Union, List
from enum import Enum
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import asyncio

logger = logging.getLogger(__name__)

class ErrorCode(str, Enum):
    """Standardized error codes."""
    
    # Authentication & Authorization
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    
    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    
    # Resources
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    RESOURCE_LIMIT_EXCEEDED = "RESOURCE_LIMIT_EXCEEDED"
    
    # Business Logic
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    OPERATION_NOT_ALLOWED = "OPERATION_NOT_ALLOWED"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    
    # System & Infrastructure
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    DATABASE_ERROR = "DATABASE_ERROR"
    CACHE_ERROR = "CACHE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    
    # AI & Governance
    AI_EXECUTION_ERROR = "AI_EXECUTION_ERROR"
    AI_PROVIDER_ERROR = "AI_PROVIDER_ERROR"
    GOVERNANCE_REJECTION = "GOVERNANCE_REJECTION"
    RISK_THRESHOLD_EXCEEDED = "RISK_THRESHOLD_EXCEEDED"
    
    # Rate Limiting
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    TOO_MANY_REQUESTS = "TOO_MANY_REQUESTS"
    
    # Network & Connectivity
    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    CONNECTION_ERROR = "CONNECTION_ERROR"

class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorContext(BaseModel):
    """Error context information."""
    user_id: Optional[str] = None
    workspace_id: Optional[str] = None
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    endpoint: Optional[str] = None
    method: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    additional_data: Dict[str, Any] = Field(default_factory=dict)

class ErrorDetail(BaseModel):
    """Detailed error information."""
    code: ErrorCode
    message: str
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    context: ErrorContext
    details: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None
    retry_after: Optional[int] = None
    stack_trace: Optional[str] = None

class ErrorResponse(BaseModel):
    """Standardized error response."""
    error: ErrorDetail
    success: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SOVEREIGNException(Exception):
    """Base exception for SOVEREIGN AI backend."""
    
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None,
        retry_after: Optional[int] = None,
        context: Optional[ErrorContext] = None
    ):
        self.code = code
        self.message = message
        self.severity = severity
        self.details = details or {}
        self.suggestions = suggestions or []
        self.retry_after = retry_after
        self.context = context or ErrorContext()
        super().__init__(message)

class ValidationError(SOVEREIGNException):
    """Validation error."""
    
    def __init__(self, message: str, field: str = None, value: Any = None, **kwargs):
        details = kwargs.get('details', {})
        if field:
            details['field'] = field
        if value is not None:
            details['value'] = str(value)
        
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            details=details,
            **kwargs
        )

class AuthenticationError(SOVEREIGNException):
    """Authentication error."""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            code=ErrorCode.UNAUTHORIZED,
            message=message,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )

class AuthorizationError(SOVEREIGNException):
    """Authorization error."""
    
    def __init__(self, message: str = "Access denied", **kwargs):
        super().__init__(
            code=ErrorCode.FORBIDDEN,
            message=message,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )

class ResourceNotFoundError(SOVEREIGNException):
    """Resource not found error."""
    
    def __init__(self, resource_type: str, resource_id: str = None, **kwargs):
        message = f"{resource_type} not found"
        if resource_id:
            message += f" with ID: {resource_id}"
        
        details = kwargs.get('details', {})
        details['resource_type'] = resource_type
        if resource_id:
            details['resource_id'] = resource_id
        
        super().__init__(
            code=ErrorCode.NOT_FOUND,
            message=message,
            details=details,
            **kwargs
        )

class BusinessRuleError(SOVEREIGNException):
    """Business rule violation error."""
    
    def __init__(self, message: str, rule: str = None, **kwargs):
        details = kwargs.get('details', {})
        if rule:
            details['violated_rule'] = rule
        
        super().__init__(
            code=ErrorCode.BUSINESS_RULE_VIOLATION,
            message=message,
            details=details,
            **kwargs
        )

class AIExecutionError(SOVEREIGNException):
    """AI execution error."""
    
    def __init__(self, message: str, provider: str = None, model: str = None, **kwargs):
        details = kwargs.get('details', {})
        if provider:
            details['provider'] = provider
        if model:
            details['model'] = model
        
        super().__init__(
            code=ErrorCode.AI_EXECUTION_ERROR,
            message=message,
            details=details,
            **kwargs
        )

class RateLimitError(SOVEREIGNException):
    """Rate limit error."""
    
    def __init__(self, limit: int, window: int, **kwargs):
        message = f"Rate limit exceeded: {limit} requests per {window} seconds"
        
        details = kwargs.get('details', {})
        details['limit'] = limit
        details['window'] = window
        
        super().__init__(
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message=message,
            retry_after=window,
            details=details,
            **kwargs
        )

class ErrorHandler:
    """Centralized error handler."""
    
    def __init__(self):
        self.error_callbacks: Dict[ErrorCode, List[callable]] = {}
        self.error_stats: Dict[str, int] = {}
    
    def register_callback(self, code: ErrorCode, callback: callable):
        """Register error callback."""
        if code not in self.error_callbacks:
            self.error_callbacks[code] = []
        self.error_callbacks[code].append(callback)
    
    async def handle_exception(
        self, 
        exception: Exception, 
        request: Optional[Request] = None
    ) -> ErrorResponse:
        """Handle exception and create standardized response."""
        
        # Determine error type and create error detail
        if isinstance(exception, SOVEREIGNException):
            error_detail = await self._create_sovereign_error_detail(exception, request)
        elif isinstance(exception, HTTPException):
            error_detail = await self._create_http_error_detail(exception, request)
        else:
            error_detail = await self._create_system_error_detail(exception, request)
        
        # Log error
        await self._log_error(error_detail, exception)
        
        # Update statistics
        self._update_stats(error_detail.error.code)
        
        # Execute callbacks
        await self._execute_callbacks(error_detail.error.code, error_detail, exception)
        
        # Create error response
        return ErrorResponse(error=error_detail)
    
    async def _create_sovereign_error_detail(
        self, 
        exception: SOVEREIGNException, 
        request: Optional[Request]
    ) -> ErrorDetail:
        """Create error detail from SOVEREIGN exception."""
        context = exception.context
        if request:
            context = self._enrich_context_from_request(context, request)
        
        return ErrorDetail(
            code=exception.code,
            message=exception.message,
            severity=exception.severity,
            context=context,
            details=exception.details,
            suggestions=exception.suggestions,
            retry_after=exception.retry_after
        )
    
    async def _create_http_error_detail(
        self, 
        exception: HTTPException, 
        request: Optional[Request]
    ) -> ErrorDetail:
        """Create error detail from HTTP exception."""
        context = ErrorContext()
        if request:
            context = self._enrich_context_from_request(context, request)
        
        # Map HTTP status to error code
        error_code_mapping = {
            400: ErrorCode.VALIDATION_ERROR,
            401: ErrorCode.UNAUTHORIZED,
            403: ErrorCode.FORBIDDEN,
            404: ErrorCode.NOT_FOUND,
            409: ErrorCode.RESOURCE_CONFLICT,
            429: ErrorCode.RATE_LIMIT_EXCEEDED,
            500: ErrorCode.INTERNAL_SERVER_ERROR,
            502: ErrorCode.EXTERNAL_SERVICE_ERROR,
            503: ErrorCode.SERVICE_UNAVAILABLE
        }
        
        code = error_code_mapping.get(exception.status_code, ErrorCode.INTERNAL_SERVER_ERROR)
        
        return ErrorDetail(
            code=code,
            message=exception.detail,
            context=context,
            details={"status_code": exception.status_code}
        )
    
    async def _create_system_error_detail(
        self, 
        exception: Exception, 
        request: Optional[Request]
    ) -> ErrorDetail:
        """Create error detail from system exception."""
        context = ErrorContext()
        if request:
            context = self._enrich_context_from_request(context, request)
        
        return ErrorDetail(
            code=ErrorCode.INTERNAL_SERVER_ERROR,
            message="An internal server error occurred",
            severity=ErrorSeverity.HIGH,
            context=context,
            details={"exception_type": type(exception).__name__},
            stack_trace=traceback.format_exc()
        )
    
    def _enrich_context_from_request(self, context: ErrorContext, request: Request) -> ErrorContext:
        """Enrich error context with request information."""
        context.endpoint = str(request.url.path)
        context.method = request.method
        context.ip_address = request.client.host if request.client else None
        context.user_agent = request.headers.get("user-agent")
        
        # Add user and workspace info if available
        if hasattr(request.state, 'user_id'):
            context.user_id = request.state.user_id
        if hasattr(request.state, 'workspace_id'):
            context.workspace_id = request.state.workspace_id
        
        return context
    
    async def _log_error(self, error_detail: ErrorDetail, exception: Exception):
        """Log error with appropriate level."""
        log_data = {
            "error_code": error_detail.error.code,
            "message": error_detail.message,
            "severity": error_detail.severity,
            "request_id": error_detail.context.request_id,
            "user_id": error_detail.context.user_id,
            "workspace_id": error_detail.context.workspace_id,
            "endpoint": error_detail.context.endpoint
        }
        
        if error_detail.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            logger.error(f"High severity error: {log_data}", exc_info=exception)
        elif error_detail.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"Medium severity error: {log_data}")
        else:
            logger.info(f"Low severity error: {log_data}")
    
    def _update_stats(self, error_code: ErrorCode):
        """Update error statistics."""
        code_str = str(error_code)
        self.error_stats[code_str] = self.error_stats.get(code_str, 0) + 1
    
    async def _execute_callbacks(
        self, 
        code: ErrorCode, 
        error_detail: ErrorDetail, 
        exception: Exception
    ):
        """Execute registered error callbacks."""
        callbacks = self.error_callbacks.get(code, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(error_detail, exception)
                else:
                    callback(error_detail, exception)
            except Exception as callback_error:
                logger.error(f"Error in callback: {callback_error}")
    
    def get_error_stats(self) -> Dict[str, int]:
        """Get error statistics."""
        return self.error_stats.copy()

# Global error handler instance
error_handler = ErrorHandler()

# Decorator for error handling
def handle_errors(
    default_error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
    log_errors: bool = True
):
    """Decorator for automatic error handling."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except SOVEREIGNException:
                raise  # Re-raise SOVEREIGN exceptions
            except Exception as e:
                if log_errors:
                    logger.error(f"Unhandled error in {func.__name__}: {e}", exc_info=True)
                raise SOVEREIGNException(
                    code=default_error_code,
                    message=f"An error occurred in {func.__name__}",
                    details={"function": func.__name__, "original_error": str(e)}
                )
        return wrapper
    return decorator

# Recovery mechanisms
class RetryMechanism:
    """Retry mechanism for recoverable errors."""
    
    @staticmethod
    async def retry_with_backoff(
        func: callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        retryable_errors: List[ErrorCode] = None
    ):
        """Retry function with exponential backoff."""
        if retryable_errors is None:
            retryable_errors = [
                ErrorCode.EXTERNAL_SERVICE_ERROR,
                ErrorCode.DATABASE_ERROR,
                ErrorCode.CACHE_ERROR,
                ErrorCode.TIMEOUT_ERROR
            ]
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return await func()
            except SOVEREIGNException as e:
                if e.code not in retryable_errors or attempt == max_retries:
                    raise
                
                delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                logger.warning(f"Retrying in {delay}s (attempt {attempt + 1}/{max_retries + 1})")
                await asyncio.sleep(delay)
                last_exception = e
            except Exception as e:
                if attempt == max_retries:
                    raise SOVEREIGNException(
                        code=ErrorCode.INTERNAL_SERVER_ERROR,
                        message=f"Failed after {max_retries} retries",
                        details={"original_error": str(e)}
                    )
                
                delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                await asyncio.sleep(delay)
                last_exception = e
        
        raise last_exception

# Circuit breaker pattern
class CircuitBreaker:
    """Circuit breaker for external services."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func: callable, *args, **kwargs):
        """Call function with circuit breaker protection."""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise SOVEREIGNException(
                    code=ErrorCode.SERVICE_UNAVAILABLE,
                    message="Service temporarily unavailable (circuit breaker open)",
                    retry_after=self.recovery_timeout
                )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset."""
        return (
            self.last_failure_time and
            (datetime.utcnow() - self.last_failure_time).seconds >= self.recovery_timeout
        )
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

# FastAPI error handler
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for FastAPI."""
    error_response = await error_handler.handle_exception(exc, request)
    
    # Determine HTTP status code
    status_code_mapping = {
        ErrorCode.UNAUTHORIZED: 401,
        ErrorCode.FORBIDDEN: 403,
        ErrorCode.NOT_FOUND: 404,
        ErrorCode.VALIDATION_ERROR: 400,
        ErrorCode.RATE_LIMIT_EXCEEDED: 429,
        ErrorCode.SERVICE_UNAVAILABLE: 503,
        ErrorCode.INTERNAL_SERVER_ERROR: 500
    }
    
    status_code = status_code_mapping.get(
        error_response.error.code, 
        500
    )
    
    # Add retry-after header if applicable
    headers = {}
    if error_response.error.retry_after:
        headers["Retry-After"] = str(error_response.error.retry_after)
    
    return JSONResponse(
        status_code=status_code,
        content=error_response.dict(),
        headers=headers
    )
