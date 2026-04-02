"""
User Dashboard - Read-Only View
==============================

User dashboard that shows system status but doesn't allow control.
Users can see what's enabled/disabled but cannot change switches.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from apps.api.routers.dashboard_auth import get_any_user
from apps.api.routers.admin_dashboard import admin_dashboard_service

router = APIRouter(prefix="/user/dashboard", tags=["user-dashboard"])
USER_VISIBLE_CATEGORIES = {"AI System", "Features", "Monitoring", "Security"}

class ReadOnlySwitch(BaseModel):
    """Read-only switch information for users."""
    name: str
    display_name: str
    description: str
    enabled: bool
    category: str
    status_message: str

class UserDashboardView(BaseModel):
    """User dashboard view (read-only)."""
    switches: List[ReadOnlySwitch]
    system_status: Dict[str, Any]
    feature_summary: Dict[str, Any]
    last_updated: datetime

class UserDashboardService:
    """Service for user dashboard (read-only)."""
    
    def get_user_dashboard_view(self, user_id: str, workspace_id: str) -> UserDashboardView:
        """Get read-only dashboard view for user."""
        
        switches = admin_dashboard_service.load_switches()
        visible_switches = self.filter_visible_switches(switches)
        read_only_switches = []
        
        for switch in visible_switches:
            status_message = self.get_switch_status_message(switch)
            read_only_switches.append(ReadOnlySwitch(
                name=switch.name,
                display_name=switch.display_name,
                description=switch.description,
                enabled=switch.enabled,
                category=switch.category,
                status_message=status_message
            ))
        
        system_status = self.sanitize_system_status(admin_dashboard_service.get_system_status())
        feature_summary = self.get_feature_summary(visible_switches)
        
        return UserDashboardView(
            switches=read_only_switches,
            system_status=system_status,
            feature_summary=feature_summary,
            last_updated=datetime.now()
        )
    
    def filter_visible_switches(self, switches: List) -> List:
        """Limit switches exposed to end users."""
        return [s for s in switches if s.category in USER_VISIBLE_CATEGORIES]
    
    def get_switch_status_message(self, switch) -> str:
        """Get user-friendly status message for switch."""
        if switch.enabled:
            return f"✅ {switch.display_name} is active and available"
        else:
            return f"❌ {switch.display_name} is currently disabled"
    
    def sanitize_system_status(self, status: Dict[str, Any]) -> Dict[str, Any]:
        """Expose only high-level status fields for users."""
        return {
            "server_status": status.get("server_status", "unknown"),
            "message": "System is operational" if status.get("server_status") == "running" else "System issues detected",
            "last_restart": status.get("last_restart", datetime.now().isoformat())
        }
    
    def get_feature_summary(self, switches: List) -> Dict[str, Any]:
        """Get feature availability summary for users."""
        
        categories = {}
        for switch in switches:
            if switch.category not in categories:
                categories[switch.category] = {
                    "total": 0,
                    "enabled": 0,
                    "disabled": 0,
                    "available_features": []
                }
            
            categories[switch.category]["total"] += 1
            if switch.enabled:
                categories[switch.category]["enabled"] += 1
                categories[switch.category]["available_features"].append(switch.display_name)
            else:
                categories[switch.category]["disabled"] += 1
        
        # Overall availability
        total_switches = len(switches)
        enabled_switches = sum(1 for switch in switches if switch.enabled)
        
        return {
            "overall_availability": {
                "total_features": total_switches,
                "available_features": enabled_switches,
                "unavailable_features": total_switches - enabled_switches,
                "availability_percentage": (enabled_switches / total_switches) * 100 if total_switches > 0 else 0
            },
            "by_category": categories,
            "key_features_status": {
                "ai_system": any(s.name == "ai_execution_enabled" and s.enabled for s in switches),
                "billing": any(s.name == "stripe_billing_enabled" and s.enabled for s in switches),
                "security": any(s.name == "authentication_required" and s.enabled for s in switches),
                "monitoring": any(s.name == "health_checks_enabled" and s.enabled for s in switches)
            }
        }

# Global service instance
user_dashboard_service = UserDashboardService()

@router.get("/view", response_model=UserDashboardView)
async def get_user_dashboard(
    current_user: dict = Depends(get_any_user)
):
    """Get user dashboard view (read-only)."""
    
    return user_dashboard_service.get_user_dashboard_view(current_user["username"], current_user["id"])

@router.get("/features")
async def get_available_features(
    current_user: dict = Depends(get_any_user)
):
    """Get list of available features for user."""
    
    switches = admin_dashboard_service.load_switches()
    available_features = []
    
    for switch in switches:
        if switch.enabled:
            available_features.append({
                "name": switch.name,
                "display_name": switch.display_name,
                "description": switch.description,
                "category": switch.category
            })
    
    return {
        "available_features": available_features,
        "total_available": len(available_features),
        "timestamp": datetime.now().isoformat()
    }

@router.get("/system-status")
async def get_user_system_status(
    current_user: dict = Depends(get_any_user)
):
    """Get system status for user view."""
    
    system_status = admin_dashboard_service.get_system_status()
    switches = admin_dashboard_service.load_switches()
    
    # Add user-friendly status information
    user_status = {
        "server_status": system_status["server_status"],
        "message": "System is operational" if system_status["server_status"] == "running" else "System issues detected",
        "features_available": sum(1 for switch in switches if switch.enabled),
        "total_features": len(switches),
        "last_updated": system_status.get("last_restart", datetime.now().isoformat())
    }
    
    return user_status

@router.get("/announcements")
async def get_system_announcements(
    current_user: dict = Depends(get_any_user)
):
    """Get system announcements for users."""
    
    switches = admin_dashboard_service.load_switches()
    
    announcements = []
    
    # Check for disabled critical features
    critical_switches = [
        "ai_execution_enabled",
        "stripe_billing_enabled",
        "authentication_required"
    ]
    
    for switch_name in critical_switches:
        for switch in switches:
            if switch.name == switch_name and not switch.enabled:
                announcements.append({
                    "type": "warning",
                    "title": f"{switch.display_name} Disabled",
                    "message": f"The {switch.display_name} is currently disabled. Some features may not be available.",
                    "priority": "high",
                    "timestamp": switch.last_modified or datetime.now()
                })
    
    # Check for maintenance mode
    for switch in switches:
        if switch.name == "maintenance_mode_enabled" and switch.enabled:
            announcements.append({
                "type": "info",
                "title": "System Under Maintenance",
                "message": "The system is currently in maintenance mode. Some features may be temporarily unavailable.",
                "priority": "medium",
                "timestamp": switch.last_modified or datetime.now()
            })
    
    return {
        "announcements": announcements,
        "total_announcements": len(announcements),
        "timestamp": datetime.now().isoformat()
    }

@router.get("/help")
async def get_help_information(
    current_user: dict = Depends(get_any_user)
):
    """Get help information for users."""
    
    switches = admin_dashboard_service.load_switches()
    
    help_sections = {
        "ai_features": {
            "title": "AI Features",
            "description": "Information about AI execution and capabilities",
            "available": any(s.name == "ai_execution_enabled" and s.enabled for s in switches),
            "items": [
                {
                    "feature": "AI Execution",
                    "description": "Process text through AI models with governance",
                    "available": any(s.name == "ai_execution_enabled" and s.enabled for s in switches)
                },
                {
                    "feature": "Risk Assessment",
                    "description": "Automatic risk scoring and content validation",
                    "available": any(s.name == "risk_assessment_enabled" and s.enabled for s in switches)
                }
            ]
        },
        "billing": {
            "title": "Billing & Subscriptions",
            "description": "Payment processing and subscription management",
            "available": any(s.name == "stripe_billing_enabled" and s.enabled for s in switches),
            "items": [
                {
                    "feature": "Payment Processing",
                    "description": "Secure payment processing through Stripe",
                    "available": any(s.name == "stripe_billing_enabled" and s.enabled for s in switches)
                },
                {
                    "feature": "Subscription Management",
                    "description": "Manage subscriptions and billing cycles",
                    "available": any(s.name == "subscription_management_enabled" and s.enabled for s in switches)
                }
            ]
        },
        "security": {
            "title": "Security & Privacy",
            "description": "Security features and privacy protections",
            "available": any(s.name == "authentication_required" and s.enabled for s in switches),
            "items": [
                {
                    "feature": "Authentication",
                    "description": "Secure user authentication and authorization",
                    "available": any(s.name == "authentication_required" and s.enabled for s in switches)
                },
                {
                    "feature": "Audit Logging",
                    "description": "Comprehensive audit logging for compliance",
                    "available": any(s.name == "audit_logging_enabled" and s.enabled for s in switches)
                }
            ]
        }
    }
    
    return {
        "help_sections": help_sections,
        "contact_support": "support@byos-ai.com",
        "documentation_url": "https://docs.byos-ai.com",
        "timestamp": datetime.now().isoformat()
    }
