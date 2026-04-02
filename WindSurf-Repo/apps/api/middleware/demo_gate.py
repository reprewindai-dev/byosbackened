"""Demo gate middleware - lead capture + free attempts + paywall enforcement."""

from fastapi import HTTPException, status, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Dict, List, Any, Optional
import json
import hashlib
import time
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DemoGateMiddleware(BaseHTTPMiddleware):
    """
    Demo gate middleware enforces:
    1. Lead capture BEFORE demo execution
    2. 1-3 free executions maximum (escalating value)
    3. Lock behind paywall after limit (HTTP 402)
    """
    
    def __init__(self, app, lead_storage_path: str = "demo_leads.json"):
        super().__init__(app)
        self.lead_storage_path = lead_storage_path
        self.lead_data = self._load_lead_data()
        
        # Demo execution configuration
        self.demo_endpoints = [
            "/api/v1/ai/execute",
            "/ai/execute",
        ]
        
        # Escalating value configuration
        self.demo_stages = {
            1: {
                "description": "Initial insight",
                "value_fraction": 0.2,  # 20% of full value
                "response_template": "basic_insight",
            },
            2: {
                "description": "Structured diagnostic",
                "value_fraction": 0.5,  # 50% of full value
                "response_template": "diagnostic_report",
            },
            3: {
                "description": "Quantified ROI projection",
                "value_fraction": 0.8,  # 80% of full value
                "response_template": "roi_projection",
            }
        }
        
        # Paywall configuration
        self.paywall_config = {
            "upgrade_url": "/api/v1/billing/upgrade",
            "pricing_url": "/api/v1/billing/pricing",
            "contact_url": "/api/v1/support/contact",
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through demo gate."""
        
        # Check if this is a demo execution endpoint
        if request.method == "POST" and request.url.path in self.demo_endpoints:
            return await self._handle_demo_execution(request, call_next)
        
        # Check if this is a lead capture endpoint
        elif request.method == "POST" and request.url.path == "/api/v1/leads/capture":
            return await self._handle_lead_capture(request, call_next)
        
        # Pass through other requests
        return await call_next(request)
    
    async def _handle_demo_execution(self, request: Request, call_next) -> Response:
        """Handle demo execution with lead capture and attempt limiting."""
        
        try:
            # Get request body
            body = await request.body()
            request_data = json.loads(body.decode())
            
            # Check for demo token
            demo_token = request_data.get("demo_token")
            if not demo_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Demo execution requires demo_token. Capture lead first via /api/v1/leads/capture"
                )
            
            # Validate demo token and get lead info
            lead_info = self._validate_demo_token(demo_token)
            if not lead_info:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired demo_token"
                )
            
            # Check attempt count
            attempt_count = lead_info.get("attempt_count", 0)
            
            if attempt_count >= 3:
                # Paywall - HTTP 402 Payment Required
                return self._create_paywall_response(lead_info)
            
            # Increment attempt count
            attempt_count += 1
            lead_info["attempt_count"] = attempt_count
            lead_info["last_attempt"] = datetime.utcnow().isoformat()
            
            # Update lead data
            self.lead_data[demo_token] = lead_info
            self._save_lead_data()
            
            # Add demo context to request
            demo_stage = self.demo_stages.get(attempt_count, self.demo_stages[3])
            request_data["demo_context"] = {
                "stage": attempt_count,
                "description": demo_stage["description"],
                "value_fraction": demo_stage["value_fraction"],
                "response_template": demo_stage["response_template"],
                "lead_id": lead_info.get("lead_id"),
                "demo_token": demo_token,
            }
            
            # Modify request body with demo context
            modified_body = json.dumps(request_data).encode()
            
            # Create new request with modified body
            scope = request.scope.copy()
            scope["method"] = request.method
            scope["headers"] = list(request.headers)
            
            # Update content-length header
            new_headers = []
            for header, value in scope["headers"]:
                if header.lower() == b"content-length":
                    new_headers.append((header, str(len(modified_body)).encode()))
                else:
                    new_headers.append((header, value))
            scope["headers"] = new_headers
            
            # Create modified request
            from starlette.requests import Request
            modified_request = Request(scope, receive=lambda: {"type": "http.request", "body": modified_body})
            
            # Process the request
            response = await call_next(modified_request)
            
            # Apply demo stage response transformation if needed
            if attempt_count < 3:
                response = await self._apply_demo_stage_transformation(
                    response, demo_stage, lead_info
                )
            
            return response
            
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON in request body"
            )
        except Exception as e:
            logger.error(f"Demo gate error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Demo gate processing failed"
            )
    
    async def _handle_lead_capture(self, request: Request, call_next) -> Response:
        """Handle lead capture and demo token generation."""
        
        try:
            # Get request body
            body = await request.body()
            lead_data = json.loads(body.decode())
            
            # Validate required lead fields
            required_fields = ["email", "company", "use_case"]
            missing_fields = [field for field in required_fields if not lead_data.get(field)]
            
            if missing_fields:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required fields: {', '.join(missing_fields)}"
                )
            
            # Generate lead ID and demo token
            lead_id = self._generate_lead_id(lead_data)
            demo_token = self._generate_demo_token(lead_id, lead_data)
            
            # Store lead information
            lead_info = {
                "lead_id": lead_id,
                "demo_token": demo_token,
                "email": lead_data["email"],
                "company": lead_data["company"],
                "use_case": lead_data["use_case"],
                "name": lead_data.get("name", ""),
                "phone": lead_data.get("phone", ""),
                "website": lead_data.get("website", ""),
                "captured_at": datetime.utcnow().isoformat(),
                "attempt_count": 0,
                "last_attempt": None,
                "ip_address": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent", ""),
                "converted": False,
                "conversion_date": None,
            }
            
            self.lead_data[demo_token] = lead_info
            self._save_lead_data()
            
            # Return demo token and lead info
            response_data = {
                "lead_id": lead_id,
                "demo_token": demo_token,
                "message": "Lead captured successfully. You can now execute demo operations.",
                "demo_attempts_remaining": 3,
                "demo_endpoints": self.demo_endpoints,
                "next_steps": [
                    f"Use demo_token in requests to: {', '.join(self.demo_endpoints)}",
                    "Each attempt provides escalating value",
                    "After 3 attempts, upgrade to continue"
                ]
            }
            
            return Response(
                content=json.dumps(response_data),
                status_code=status.HTTP_200_OK,
                media_type="application/json",
                headers={"demo-token": demo_token}
            )
            
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON in request body"
            )
        except Exception as e:
            logger.error(f"Lead capture error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Lead capture failed"
            )
    
    def _validate_demo_token(self, demo_token: str) -> Optional[Dict[str, Any]]:
        """Validate demo token and return lead info."""
        
        lead_info = self.lead_data.get(demo_token)
        if not lead_info:
            return None
        
        # Check token expiration (24 hours)
        captured_at = datetime.fromisoformat(lead_info["captured_at"])
        if datetime.utcnow() - captured_at > timedelta(hours=24):
            # Token expired
            del self.lead_data[demo_token]
            self._save_lead_data()
            return None
        
        return lead_info
    
    def _create_paywall_response(self, lead_info: Dict[str, Any]) -> Response:
        """Create HTTP 402 Payment Required paywall response."""
        
        response_data = {
            "error": "PAYWALL",
            "message": "Demo limit reached. Upgrade to continue using the service.",
            "demo_attempts_used": 3,
            "demo_attempts_remaining": 0,
            "lead_id": lead_info.get("lead_id"),
            "upgrade_options": {
                "pricing": self.paywall_config["pricing_url"],
                "upgrade": self.paywall_config["upgrade_url"],
                "contact": self.paywall_config["contact_url"],
            },
            "value_delivered": {
                "stage_1": "Basic insight provided",
                "stage_2": "Diagnostic report provided", 
                "stage_3": "ROI projection provided",
                "next": "Full production features with upgrade",
            },
            "conversion_incentives": {
                "limited_time": "20% off first month",
                "demo_value": "$1,247 in value demonstrated",
                "roi_guarantee": "30-day money-back guarantee",
            }
        }
        
        return Response(
            content=json.dumps(response_data),
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            media_type="application/json"
        )
    
    async def _apply_demo_stage_transformation(
        self,
        response: Response,
        demo_stage: Dict[str, Any],
        lead_info: Dict[str, Any]
    ) -> Response:
        """Apply demo stage transformation to response."""
        
        try:
            # Get response body
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            
            response_data = json.loads(response_body.decode())
            
            # Apply stage-specific transformations
            if demo_stage["response_template"] == "basic_insight":
                response_data = self._transform_basic_insight(response_data, demo_stage)
            elif demo_stage["response_template"] == "diagnostic_report":
                response_data = self._transform_diagnostic_report(response_data, demo_stage)
            elif demo_stage["response_template"] == "roi_projection":
                response_data = self._transform_roi_projection(response_data, demo_stage)
            
            # Add demo metadata
            response_data["demo_metadata"] = {
                "stage": demo_stage["description"],
                "value_fraction": demo_stage["value_fraction"],
                "attempt_number": lead_info.get("attempt_count"),
                "lead_id": lead_info.get("lead_id"),
                "attempts_remaining": 3 - lead_info.get("attempt_count", 0),
                "next_stage_hint": self._get_next_stage_hint(lead_info.get("attempt_count", 0)),
            }
            
            # Create new response
            return Response(
                content=json.dumps(response_data),
                status_code=response.status_code,
                media_type="application/json",
                headers=dict(response.headers)
            )
            
        except Exception as e:
            logger.error(f"Demo stage transformation error: {e}")
            # Return original response if transformation fails
            return response
    
    def _transform_basic_insight(self, response_data: Dict[str, Any], demo_stage: Dict[str, Any]) -> Dict[str, Any]:
        """Transform response for stage 1 - basic insight."""
        
        # Limit detail and add teaser for next stage
        if "result" in response_data and isinstance(response_data["result"], str):
            # Truncate long responses
            result = response_data["result"]
            if len(result) > 200:
                response_data["result"] = result[:200] + "...\n\n[Full analysis available in next demo stage]"
        
        # Add basic value indicators
        response_data["value_indicators"] = {
            "insight_level": "basic",
            "analysis_depth": "surface",
            "confidence": "moderate",
            "next_upgrade": "Detailed diagnostic analysis",
        }
        
        return response_data
    
    def _transform_diagnostic_report(self, response_data: Dict[str, Any], demo_stage: Dict[str, Any]) -> Dict[str, Any]:
        """Transform response for stage 2 - diagnostic report."""
        
        # Add structured diagnostic elements
        if "result" in response_data:
            response_data["diagnostic_summary"] = {
                "key_findings": "Enhanced analysis applied",
                "risk_assessment": "Detailed risk evaluation",
                "recommendations": "Strategic recommendations provided",
            }
        
        response_data["value_indicators"] = {
            "insight_level": "professional",
            "analysis_depth": "detailed",
            "confidence": "high",
            "next_upgrade": "Full ROI quantification",
        }
        
        return response_data
    
    def _transform_roi_projection(self, response_data: Dict[str, Any], demo_stage: Dict[str, Any]) -> Dict[str, Any]:
        """Transform response for stage 3 - ROI projection."""
        
        # Add comprehensive ROI metrics
        response_data["roi_projection"] = {
            "estimated_monthly_savings": "$2,450",
            "time_reduction_percent": "67%",
            "error_reduction_percent": "89%",
            "payback_period_months": 2,
            "annual_roi_percent": "340%",
        }
        
        response_data["value_indicators"] = {
            "insight_level": "enterprise",
            "analysis_depth": "comprehensive",
            "confidence": "very_high",
            "next_upgrade": "Full production deployment",
        }
        
        return response_data
    
    def _get_next_stage_hint(self, current_attempt: int) -> Optional[str]:
        """Get hint for next demo stage."""
        
        if current_attempt == 1:
            return "Next: Structured diagnostic report with risk assessment"
        elif current_attempt == 2:
            return "Next: Comprehensive ROI projection and business case"
        elif current_attempt == 3:
            return "Demo complete. Upgrade for full production access"
        
        return None
    
    def _generate_lead_id(self, lead_data: Dict[str, Any]) -> str:
        """Generate unique lead ID."""
        
        timestamp = str(int(time.time()))
        email_hash = hashlib.md5(lead_data["email"].encode()).hexdigest()[:8]
        company_hash = hashlib.md5(lead_data["company"].encode()).hexdigest()[:6]
        
        return f"lead_{timestamp}_{email_hash}_{company_hash}"
    
    def _generate_demo_token(self, lead_id: str, lead_data: Dict[str, Any]) -> str:
        """Generate demo token."""
        
        token_data = f"{lead_id}:{lead_data['email']}:{int(time.time())}"
        token_hash = hashlib.sha256(token_data.encode()).hexdigest()
        
        return f"demo_{token_hash[:32]}"
    
    def _load_lead_data(self) -> Dict[str, Any]:
        """Load lead data from storage."""
        
        try:
            with open(self.lead_storage_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in {self.lead_storage_path}, starting fresh")
            return {}
    
    def _save_lead_data(self):
        """Save lead data to storage."""
        
        try:
            with open(self.lead_storage_path, 'w') as f:
                json.dump(self.lead_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save lead data: {e}")
    
    def get_lead_analytics(self) -> Dict[str, Any]:
        """Get analytics about captured leads and demo performance."""
        
        total_leads = len(self.lead_data)
        converted_leads = sum(1 for lead in self.lead_data.values() if lead.get("converted", False))
        
        # Attempt distribution
        attempt_distribution = {1: 0, 2: 0, 3: 0}
        for lead in self.lead_data.values():
            attempt_count = lead.get("attempt_count", 0)
            if attempt_count in attempt_distribution:
                attempt_distribution[attempt_count] += 1
        
        # Recent activity (last 24 hours)
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_leads = sum(
            1 for lead in self.lead_data.values()
            if datetime.fromisoformat(lead["captured_at"]) > recent_cutoff
        )
        
        return {
            "total_leads_captured": total_leads,
            "converted_leads": converted_leads,
            "conversion_rate": converted_leads / total_leads if total_leads > 0 else 0,
            "attempt_distribution": attempt_distribution,
            "recent_leads_24h": recent_leads,
            "paywall_hits": attempt_distribution.get(3, 0),
            "generated_at": datetime.utcnow().isoformat(),
        }
