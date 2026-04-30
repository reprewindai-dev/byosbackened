"""Database models."""
from db.models.workspace import Workspace
from db.models.user import User, UserRole, UserStatus
from db.models.job import Job, JobType, JobStatus
from db.models.asset import Asset
from db.models.transcript import Transcript
from db.models.export import Export, ExportFormat
from db.models.cost_prediction import CostPrediction
from db.models.routing_decision import RoutingDecision
from db.models.ai_audit import AIAuditLog
from db.models.cost_allocation import CostAllocation
from db.models.budget import Budget
from db.models.security_audit import SecurityAuditLog
from db.models.abuse_log import AbuseLog
from db.models.incident_log import IncidentLog
from db.models.routing_policy import RoutingPolicy
from db.models.ml_model import MLModel
from db.models.deployment import Deployment, DeploymentStatus
from db.models.routing_strategy import RoutingStrategy
from db.models.traffic_pattern import TrafficPattern
from db.models.anomaly import Anomaly
from db.models.savings_report import SavingsReport
from db.models.security_event import SecurityEvent, ThreatType, SecurityLevel
from db.models.user_session import UserSession
from db.models.api_key import APIKey
from db.models.workspace_request_log import WorkspaceRequestLog
from db.models.workspace_model_setting import WorkspaceModelSetting
from db.models.subscription import Subscription, PlanTier, SubscriptionStatus
from license.tier import LicenseTier
try:
    from db.models.license_key import LicenseKey
except ImportError:  # buyer package excludes the server-side license service model
    LicenseKey = None
from db.models.content_filter import ContentFilterLog, AgeVerification, ContentCategory, AgeVerificationStatus
from db.models.system_metrics import SystemMetrics
from db.models.alert import Alert, AlertSeverity
from db.models.execution_log import ExecutionLog
from db.models.token_wallet import TokenWallet, TokenTransaction


def _optional_import(path: str, names: tuple[str, ...]) -> tuple[object, ...]:
    try:
        module = __import__(path, fromlist=list(names))
    except ImportError:
        return tuple(None for _ in names)
    return tuple(getattr(module, name) for name in names)


Vendor, = _optional_import("db.models.vendor", ("Vendor",))
Listing, = _optional_import("db.models.listing", ("Listing",))
MarketplaceFile, = _optional_import("db.models.marketplace_file", ("MarketplaceFile",))
EvidencePackage, = _optional_import("db.models.evidence_package", ("EvidencePackage",))
MarketplaceOrder, MarketplaceOrderItem = _optional_import("db.models.marketplace_order", ("MarketplaceOrder", "MarketplaceOrderItem"))
MarketplacePayout, = _optional_import("db.models.marketplace_payout", ("MarketplacePayout",))
GithubInstallation, GithubRepo = _optional_import("db.models.github_installation", ("GithubInstallation", "GithubRepo"))
UsageEvent, = _optional_import("db.models.usage_event", ("UsageEvent",))
ComplianceReview, = _optional_import("db.models.compliance_review", ("ComplianceReview",))

__all__ = [
    "Workspace",
    "User", "UserRole", "UserStatus",
    "Job", "JobType", "JobStatus",
    "Asset",
    "Transcript",
    "Export", "ExportFormat",
    "CostPrediction",
    "RoutingDecision",
    "AIAuditLog",
    "CostAllocation",
    "Budget",
    "SecurityAuditLog",
    "AbuseLog",
    "IncidentLog",
    "RoutingPolicy",
    "MLModel",
    "Deployment", "DeploymentStatus",
    "RoutingStrategy",
    "TrafficPattern",
    "Anomaly",
    "SavingsReport",
    "SecurityEvent", "ThreatType", "SecurityLevel",
    "UserSession",
    "APIKey",
    "WorkspaceRequestLog",
    "WorkspaceModelSetting",
    "Subscription", "PlanTier", "SubscriptionStatus",
    "LicenseTier",
    "ContentFilterLog", "AgeVerification", "ContentCategory", "AgeVerificationStatus",
    "SystemMetrics",
    "Alert", "AlertSeverity",
    "ExecutionLog",
    "TokenWallet", "TokenTransaction",
    "Vendor",
    "Listing",
    "MarketplaceFile",
    "EvidencePackage",
    "MarketplaceOrder", "MarketplaceOrderItem",
    "MarketplacePayout",
    "GithubInstallation", "GithubRepo",
    "UsageEvent",
    "ComplianceReview",
]

if LicenseKey is not None:
    __all__.insert(__all__.index("LicenseTier"), "LicenseKey")

for optional_name in [
    "Vendor",
    "Listing",
    "MarketplaceFile",
    "EvidencePackage",
    "MarketplaceOrder",
    "MarketplaceOrderItem",
    "MarketplacePayout",
    "GithubInstallation",
    "GithubRepo",
    "UsageEvent",
    "ComplianceReview",
]:
    if globals().get(optional_name) is not None:
        __all__.append(optional_name)
