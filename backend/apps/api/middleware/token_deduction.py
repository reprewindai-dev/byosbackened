"""Token deduction middleware - deducts tokens per API request."""
import json
import logging
import uuid
from typing import Dict, Optional
from decimal import Decimal
from datetime import datetime

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from sqlalchemy.orm import Session

from db.session import SessionLocal
from db.models import TokenWallet, TokenTransaction
from core.redis_pool import get_redis
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Public endpoints that don't require token deduction
PUBLIC_ENDPOINTS = {
    "/health",
    "/",
    "/status",
    "/metrics",
    # Docs now cost tokens - pay per call
    # "/api/v1/docs": 100,  # Moved to costing
    # "/api/v1/redoc": 100,  # Moved to costing
    "/api/v1/openapi.json",  # Free for SDKs
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/subscriptions/plans",
    "/api/v1/subscriptions/webhook",
}

# Default token costs by endpoint pattern
# More specific patterns should come before general ones
DEFAULT_ENDPOINT_COSTS: Dict[str, int] = {
    # Free metadata
    "/api/v1/auth/me": 0,
    "/api/v1/auth/mfa": 0,
    "/api/v1/auth/api-keys": 0,
    "/api/v1/subscriptions/current": 0,
    
    # Low cost (10 tokens)
    "/api/v1/compliance/regulations": 10,
    "/api/v1/plugins": 10,
    "/api/v1/plugins/{name}/docs": 10,
    
    # Standard cost (25 tokens)
    "/api/v1/cost/predict": 25,
    "/api/v1/cost/history": 25,
    "/api/v1/routing/policy": 25,
    "/api/v1/routing/test": 25,
    "/api/v1/budget": 25,
    "/api/v1/budget/forecast": 25,
    "/api/v1/billing": 30,
    "/api/v1/billing/report": 30,
    "/api/v1/billing/breakdown": 30,
    "/api/v1/insights/savings": 25,
    "/api/v1/insights/summary": 25,
    "/api/v1/insights/savings/projected": 25,
    
    # AI/ML cost (50 tokens base)
    "/api/v1/autonomous/cost/predict": 50,
    "/api/v1/autonomous/routing/select": 50,
    "/api/v1/autonomous/routing/update": 50,
    "/api/v1/autonomous/quality/predict": 50,
    "/api/v1/autonomous/quality/optimize": 50,
    "/api/v1/autonomous/quality/failure-risk": 50,
    "/api/v1/autonomous/train": 50,
    
    # Content safety (25-40 tokens)
    "/api/v1/content-safety/scan": 25,
    "/api/v1/content-safety/scan/file": 40,
    "/api/v1/content-safety/logs": 40,
    
    # Explainability (30 tokens)
    "/api/v1/explain/routing": 30,
    "/api/v1/explain/cost": 30,
    
    # Privacy (25 tokens for detect/mask)
    "/api/v1/privacy/detect-pii": 25,
    "/api/v1/privacy/mask-pii": 25,
    
    # Compliance/Audit (250-2500 tokens)
    "/api/v1/compliance/check": 250,
    "/api/v1/compliance/report": 2500,
    "/api/v1/audit/logs": 30,
    "/api/v1/audit/verify": 30,
    "/api/v1/audit/compliance-report": 2500,
    
    # Security/Locker (40-50 tokens)
    "/api/v1/security/events": 40,
    "/api/v1/security/stats": 40,
    "/api/v1/security/dashboard": 50,
    "/api/v1/security/alerts": 40,
    "/api/v1/locker/security/events": 40,
    "/api/v1/locker/security/threats": 40,
    "/api/v1/locker/security/controls": 40,
    "/api/v1/locker/security/dashboard": 50,
    
    # Monitoring (10-25 tokens)
    "/api/v1/monitoring/health": 10,
    "/api/v1/monitoring/metrics": 25,
    "/api/v1/monitoring/dashboard": 25,
    "/api/v1/monitoring/metrics/history": 25,
    "/api/v1/locker/monitoring/status": 25,
    "/api/v1/locker/monitoring/metrics/performance": 25,
    "/api/v1/locker/monitoring/alerts": 25,
    
    # Plugins (40 tokens for enable/disable)
    "/api/v1/plugins/{name}/enable": 40,
    "/api/v1/plugins/{name}/disable": 40,
    
    # Kill switch (0 tokens - admin only)
    "/api/v1/cost/kill-switch": 0,
    
    # Documentation - pay per call (100 tokens each view)
    "/api/v1/docs": 100,
    "/api/v1/redoc": 100,
}

# Variable cost endpoints - cost calculated at runtime
VARIABLE_COST_ENDPOINTS = {
    "/v1/exec": "llm_tokens",
}


class TokenDeductionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to deduct tokens from workspace wallet per API request.
    
    Enforces:
    - Check wallet balance before execution
    - Atomic deduction during request processing
    - Ledger entry for all transactions
    - 402 Payment Required on insufficient balance
    """
    
    def __init__(self, app, endpoint_costs: Optional[Dict[str, int]] = None):
        super().__init__(app)
        self.endpoint_costs = endpoint_costs or DEFAULT_ENDPOINT_COSTS
        self.variable_cost_endpoints = VARIABLE_COST_ENDPOINTS
    
    def _get_endpoint_cost(self, method: str, path: str, request: Request) -> int:
        """
        Get the token cost for an endpoint.
        Returns 0 if endpoint is free.
        """
        # Check for exact match first
        if path in self.endpoint_costs:
            return self.endpoint_costs[path]
        
        # Check for prefix match (most specific first)
        sorted_patterns = sorted(
            self.endpoint_costs.keys(),
            key=lambda x: len(x),
            reverse=True
        )
        for pattern in sorted_patterns:
            if path.startswith(pattern):
                return self.endpoint_costs[pattern]
        
        # Check for variable cost endpoints
        for var_pattern in self.variable_cost_endpoints:
            if path.startswith(var_pattern):
                # Variable cost - base cost is 0, actual cost calculated post-execution
                return 0
        
        # Default: free
        return 0
    
    def _calculate_variable_cost(self, path: str, request: Request, response) -> int:
        """
        Calculate variable cost for endpoints like LLM execution.
        Called after request processing for response-based costing.
        """
        if path.startswith("/v1/exec"):
            # Get token usage from response headers if available
            total_tokens = int(getattr(response, "headers", {}).get("X-Total-Tokens", 0))
            if total_tokens > 0:
                # Base 100 tokens + 1 per 10 input + 1 per 5 output
                # Simplified: 100 + (total_tokens / 10)
                return 100 + int(total_tokens / 10)
        
        return 0
    
    def _get_cached_balance(self, workspace_id: str) -> Optional[int]:
        """Get cached wallet balance from Redis."""
        try:
            redis = get_redis()
            key = f"wallet:balance:{workspace_id}"
            balance = redis.get(key)
            if balance:
                return int(balance)
        except Exception as e:
            logger.warning(f"Failed to get cached balance: {e}")
        return None
    
    def _cache_balance(self, workspace_id: str, balance: int, ttl: int = 300):
        """Cache wallet balance in Redis."""
        try:
            redis = get_redis()
            key = f"wallet:balance:{workspace_id}"
            redis.setex(key, ttl, str(balance))
        except Exception as e:
            logger.warning(f"Failed to cache balance: {e}")
    
    def _invalidate_balance_cache(self, workspace_id: str):
        """Invalidate cached balance after modification."""
        try:
            redis = get_redis()
            key = f"wallet:balance:{workspace_id}"
            redis.delete(key)
        except Exception as e:
            logger.warning(f"Failed to invalidate balance cache: {e}")
    
    def _deduct_tokens(
        self,
        db: Session,
        workspace_id: str,
        token_cost: int,
        endpoint_path: str,
        endpoint_method: str,
        request_id: str
    ) -> tuple[bool, int]:
        """
        Deduct tokens from wallet.
        Returns (success, new_balance).
        """
        # Get or create wallet
        wallet = db.query(TokenWallet).filter(
            TokenWallet.workspace_id == workspace_id
        ).with_for_update().first()  # Lock row for atomic update
        
        if not wallet:
            # Create wallet with 0 balance
            wallet = TokenWallet(
                workspace_id=workspace_id,
                balance=0
            )
            db.add(wallet)
            db.flush()
        
        # Check balance
        if wallet.balance < token_cost:
            return False, wallet.balance
        
        # Record transaction
        balance_before = wallet.balance
        balance_after = balance_before - token_cost
        
        transaction = TokenTransaction(
            wallet_id=wallet.id,
            workspace_id=workspace_id,
            transaction_type="usage",
            amount=-token_cost,  # Negative for deduction
            balance_before=balance_before,
            balance_after=balance_after,
            endpoint_path=endpoint_path,
            endpoint_method=endpoint_method,
            request_id=request_id,
            description=f"API usage: {endpoint_method} {endpoint_path}"
        )
        db.add(transaction)
        
        # Update wallet
        wallet.balance = balance_after
        wallet.total_credits_used = (wallet.total_credits_used or 0) + token_cost
        wallet.updated_at = datetime.utcnow()
        
        db.commit()
        
        # Invalidate cache
        self._invalidate_balance_cache(workspace_id)
        
        return True, balance_after
    
    async def dispatch(self, request: Request, call_next):
        """
        Deduct tokens for API request.
        """
        path = request.url.path
        method = request.method
        
        # Skip public endpoints
        if path in PUBLIC_ENDPOINTS:
            return await call_next(request)
        
        # Skip if no workspace_id (not authenticated)
        workspace_id = getattr(request.state, "workspace_id", None)
        if not workspace_id:
            return await call_next(request)
        
        # Generate request ID if not already set
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        request.state.request_id = request_id
        
        # Get token cost for this endpoint
        token_cost = self._get_endpoint_cost(method, path, request)
        
        # For variable cost endpoints, skip initial deduction
        is_variable_cost = any(path.startswith(p) for p in self.variable_cost_endpoints)
        
        if not is_variable_cost and token_cost > 0:
            # Check cached balance first (fast path)
            cached_balance = self._get_cached_balance(workspace_id)
            
            if cached_balance is not None and cached_balance < token_cost:
                return JSONResponse(
                    status_code=402,
                    content={
                        "detail": f"Insufficient tokens. Required: {token_cost}, Balance: {cached_balance}",
                        "required": token_cost,
                        "balance": cached_balance,
                        "purchase_url": "/api/v1/wallet/topup"
                    },
                    headers={
                        "X-Tokens-Required": str(token_cost),
                        "X-Tokens-Balance": str(cached_balance),
                        "X-Tokens-Remaining": "0"
                    }
                )
            
            # Deduct tokens atomically
            db = SessionLocal()
            try:
                success, new_balance = self._deduct_tokens(
                    db, workspace_id, token_cost, path, method, request_id
                )
                
                if not success:
                    return JSONResponse(
                        status_code=402,
                        content={
                            "detail": f"Insufficient tokens. Required: {token_cost}, Balance: {new_balance}",
                            "required": token_cost,
                            "balance": new_balance,
                            "purchase_url": "/api/v1/wallet/topup"
                        },
                        headers={
                            "X-Tokens-Required": str(token_cost),
                            "X-Tokens-Balance": str(new_balance),
                            "X-Tokens-Remaining": "0"
                        }
                    )
                
                # Store remaining tokens for response header
                request.state.remaining_tokens = new_balance
                request.state.token_cost = token_cost
                
            finally:
                db.close()
        
        # Process request
        response = await call_next(request)
        
        # Handle variable cost endpoints post-execution
        if is_variable_cost:
            variable_cost = self._calculate_variable_cost(path, request, response)
            if variable_cost > 0:
                db = SessionLocal()
                try:
                    success, new_balance = self._deduct_tokens(
                        db, workspace_id, variable_cost, path, method, request_id
                    )
                    if success:
                        request.state.remaining_tokens = new_balance
                        request.state.token_cost = variable_cost
                finally:
                    db.close()
        
        # Add token headers to response
        if hasattr(request.state, "remaining_tokens"):
            response.headers["X-Tokens-Remaining"] = str(request.state.remaining_tokens)
        if hasattr(request.state, "token_cost"):
            response.headers["X-Tokens-Cost"] = str(request.state.token_cost)
        
        return response
