"""
Enhanced API Documentation System
================================

Comprehensive API documentation with OpenAPI enhancements,
user guides, and interactive documentation.
"""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from typing import Dict, Any
import json

class APIDocumentation:
    """Enhanced API documentation system."""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.custom_openapi_schema = None
    
    def custom_openapi(self) -> Dict[str, Any]:
        """Generate custom OpenAPI schema with enhanced documentation."""
        if self.custom_openapi_schema:
            return self.custom_openapi_schema
        
        openapi_schema = get_openapi(
            title="SOVEREIGN AI SAAS STACK v1.0 - Production API",
            version="1.0.0",
            description=self._get_enhanced_description(),
            routes=self.app.routes,
        )
        
        # Add enhanced security schemes
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Enter your JWT token (without 'Bearer ' prefix)"
            }
        }
        
        # Add global security requirement
        openapi_schema["security"] = [{"BearerAuth": []}]
        
        # Add tags with descriptions
        openapi_schema["tags"] = self._get_enhanced_tags()
        
        # Add examples
        openapi_schema["components"]["examples"] = self._get_examples()
        
        # Add schemas
        openapi_schema["components"]["schemas"] = {
            **openapi_schema["components"].get("schemas", {}),
            **self._get_enhanced_schemas()
        }
        
        self.custom_openapi_schema = openapi_schema
        return openapi_schema
    
    def _get_enhanced_description(self) -> str:
        """Get enhanced API description."""
        return """
# SOVEREIGN AI SAAS STACK v1.0 - Production API

## Overview
The SOVEREIGN AI SAAS STACK is a premium, enterprise-grade AI backend system with comprehensive governance, billing, and security features.

## Key Features
- **20-Layer AI Governance Pipeline**: Advanced risk assessment and quality control
- **Multi-Provider AI Router**: HuggingFace, OpenAI, and local LLM support
- **Production Billing System**: Complete Stripe integration with subscription management
- **Enterprise Security**: Zero-trust architecture with advanced middleware
- **Real-time Dashboard**: Premium admin control center with live monitoring
- **Cost Intelligence**: Per-operation tracking with budget controls

## Authentication
All API endpoints (except authentication endpoints) require JWT authentication. 

1. Register a user account
2. Login to receive JWT token
3. Include token in Authorization header: `Bearer <token>`

## Rate Limiting
- Standard users: 100 requests per minute
- Premium users: 1000 requests per minute
- Enterprise users: 10,000 requests per minute

## Error Handling
All errors follow standard HTTP status codes with detailed error messages in JSON format.

## Support
- Documentation: https://docs.sovereign-ai.com
- Support: support@sovereign-ai.com
- Status: https://status.sovereign-ai.com
        """.strip()
    
    def _get_enhanced_tags(self) -> list:
        """Get enhanced API tags."""
        return [
            {
                "name": "Authentication",
                "description": "User registration, login, and token management"
            },
            {
                "name": "Workspaces", 
                "description": "Workspace management and collaboration"
            },
            {
                "name": "AI Execution",
                "description": "AI model execution with multiple providers"
            },
            {
                "name": "Billing",
                "description": "Cost tracking, invoices, and payment management"
            },
            {
                "name": "Dashboard",
                "description": "Analytics, monitoring, and system status"
            },
            {
                "name": "Governance",
                "description": "AI governance pipeline and risk management"
            },
            {
                "name": "Security",
                "description": "Security monitoring and compliance"
            },
            {
                "name": "ClipCrafter",
                "description": "Video content creation and management"
            },
            {
                "name": "TrapMaster Pro",
                "description": "Music production and beat creation"
            }
        ]
    
    def _get_examples(self) -> Dict[str, Any]:
        """Get API examples."""
        return {
            "UserRegistration": {
                "summary": "User Registration Example",
                "value": {
                    "email": "user@example.com",
                    "username": "username",
                    "password": "SecurePassword123!"
                }
            },
            "UserLogin": {
                "summary": "User Login Example", 
                "value": {
                    "username": "user@example.com",
                    "password": "SecurePassword123!"
                }
            },
            "AIExecution": {
                "summary": "AI Execution Example",
                "value": {
                    "provider": "huggingface",
                    "model": "distilbert-base-uncased-finetuned-sst-2-english",
                    "operation": "sentiment",
                    "prompt": "I love this product!"
                }
            },
            "WorkspaceCreation": {
                "summary": "Workspace Creation Example",
                "value": {
                    "name": "My Workspace",
                    "description": "A workspace for my AI projects"
                }
            },
            "CostAllocation": {
                "summary": "Cost Allocation Example",
                "value": {
                    "workspace_id": "workspace_123",
                    "cost": 0.01,
                    "operation": "ai_execution",
                    "provider": "huggingface",
                    "model": "sentiment-model"
                }
            }
        }
    
    def _get_enhanced_schemas(self) -> Dict[str, Any]:
        """Get enhanced schemas."""
        return {
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "detail": {
                        "type": "string",
                        "description": "Error description"
                    },
                    "error_code": {
                        "type": "string", 
                        "description": "Machine-readable error code"
                    },
                    "timestamp": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Error timestamp"
                    },
                    "request_id": {
                        "type": "string",
                        "description": "Unique request identifier"
                    }
                }
            },
            "SuccessResponse": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "description": "Response data"
                    },
                    "message": {
                        "type": "string",
                        "description": "Success message"
                    },
                    "timestamp": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Response timestamp"
                    }
                }
            },
            "PaginatedResponse": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "List of items"
                    },
                    "total": {
                        "type": "integer",
                        "description": "Total number of items"
                    },
                    "page": {
                        "type": "integer",
                        "description": "Current page number"
                    },
                    "size": {
                        "type": "integer",
                        "description": "Page size"
                    },
                    "pages": {
                        "type": "integer",
                        "description": "Total number of pages"
                    }
                }
            }
        }

def setup_enhanced_docs(app: FastAPI):
    """Setup enhanced documentation for the app."""
    docs = APIDocumentation(app)
    app.openapi = docs.custom_openapi
    return docs
