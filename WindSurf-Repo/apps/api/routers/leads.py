"""Leads router - capture + demo token mint for conversion architecture."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
import uuid
import hashlib
import time
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/leads", tags=["leads"])


class LeadCaptureRequest(BaseModel):
    """Lead capture request for demo access."""
    
    # Required fields
    email: EmailStr
    company: str
    use_case: str
    
    # Optional fields
    name: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    job_title: Optional[str] = None
    company_size: Optional[str] = None
    industry: Optional[str] = None
    
    # Source tracking
    source: Optional[str] = None  # Where they came from
    campaign: Optional[str] = None  # Marketing campaign
    referrer: Optional[str] = None  # Referral source


class LeadCaptureResponse(BaseModel):
    """Response for successful lead capture."""
    
    lead_id: str
    demo_token: str
    message: str
    demo_attempts_remaining: int
    demo_endpoints: list[str]
    next_steps: list[str]
    
    # Lead qualification info
    qualification_score: float
    estimated_value: str
    priority_level: str
    
    # Next steps timing
    follow_up_scheduled: bool
    demo_expiry_hours: int


class LeadStatusResponse(BaseModel):
    """Lead status and demo usage information."""
    
    lead_id: str
    email: str
    company: str
    
    # Demo usage
    demo_attempts_used: int
    demo_attempts_remaining: int
    demo_token_status: str  # active, expired, used_up
    
    # Lead qualification
    qualification_score: float
    engagement_level: str
    conversion_probability: float
    
    # Timing
    captured_at: datetime
    last_demo_attempt: Optional[datetime]
    demo_token_expires_at: datetime
    
    # Next actions
    recommended_next_step: str
    upgrade_incentives: Dict[str, Any]


class LeadAnalyticsResponse(BaseModel):
    """Analytics dashboard for lead performance."""
    
    # Volume metrics
    total_leads: int
    new_leads_today: int
    new_leads_this_week: int
    conversion_rate: float
    
    # Quality metrics
    avg_qualification_score: float
    high_value_leads: int
    enterprise_leads: int
    
    # Engagement metrics
    demo_completion_rate: float
    avg_demo_attempts: float
    paywall_hit_rate: float
    
    # Conversion metrics
    trials_started: int
    trials_converted: int
    time_to_conversion_days: float
    
    # Top segments
    top_industries: list[Dict[str, Any]]
    top_use_cases: list[Dict[str, Any]]
    top_company_sizes: list[Dict[str, Any]]


# In-memory storage (in production, use database)
LEAD_STORAGE = {}
DEMO_TOKENS = {}


class LeadManager:
    """Lead management system for demo conversion."""
    
    def __init__(self):
        self.qualification_weights = {
            "company_size": {
                "1-10": 0.1,
                "11-50": 0.2,
                "51-200": 0.3,
                "201-500": 0.4,
                "501-1000": 0.5,
                "1000+": 0.6,
            },
            "industry": {
                "technology": 0.3,
                "finance": 0.4,
                "healthcare": 0.4,
                "manufacturing": 0.3,
                "consulting": 0.3,
                "other": 0.2,
            },
            "use_case": {
                "content_creation": 0.3,
                "business_analysis": 0.4,
                "customer_support": 0.3,
                "data_processing": 0.4,
                "automation": 0.5,
                "other": 0.2,
            },
            "job_title": {
                "ceo": 0.5,
                "cto": 0.5,
                "vp": 0.4,
                "director": 0.4,
                "manager": 0.3,
                "analyst": 0.2,
                "other": 0.1,
            }
        }
        
        self.value_estimates = {
            "high": "$10,000+",
            "medium": "$5,000-$10,000",
            "low": "$1,000-$5,000",
        }
    
    def calculate_qualification_score(self, lead_data: Dict[str, Any]) -> float:
        """Calculate lead qualification score (0-1)."""
        
        score = 0.0
        
        # Company size weight
        company_size = lead_data.get("company_size", "").lower()
        if company_size in self.qualification_weights["company_size"]:
            score += self.qualification_weights["company_size"][company_size]
        
        # Industry weight
        industry = lead_data.get("industry", "").lower()
        if industry in self.qualification_weights["industry"]:
            score += self.qualification_weights["industry"][industry]
        else:
            score += self.qualification_weights["industry"]["other"]
        
        # Use case weight
        use_case = lead_data.get("use_case", "").lower()
        for key, weight in self.qualification_weights["use_case"].items():
            if key in use_case:
                score += weight
                break
        else:
            score += self.qualification_weights["use_case"]["other"]
        
        # Job title weight
        job_title = lead_data.get("job_title", "").lower()
        for key, weight in self.qualification_weights["job_title"].items():
            if key in job_title:
                score += weight
                break
        else:
            score += self.qualification_weights["job_title"]["other"]
        
        # Bonus signals
        if lead_data.get("website"):
            score += 0.1  # Has website = more legitimate
        
        if lead_data.get("phone"):
            score += 0.1  # Provided phone = higher engagement
        
        # Normalize to 0-1 range
        max_score = 2.2  # Maximum possible score
        return min(score / max_score, 1.0)
    
    def determine_priority_level(self, qualification_score: float) -> str:
        """Determine lead priority level."""
        
        if qualification_score >= 0.7:
            return "high"
        elif qualification_score >= 0.4:
            return "medium"
        else:
            return "low"
    
    def estimate_value(self, qualification_score: float, company_size: str) -> str:
        """Estimate deal value based on qualification."""
        
        if qualification_score >= 0.7 and company_size in ["501-1000", "1000+"]:
            return self.value_estimates["high"]
        elif qualification_score >= 0.4:
            return self.value_estimates["medium"]
        else:
            return self.value_estimates["low"]
    
    def generate_lead_id(self, lead_data: Dict[str, Any]) -> str:
        """Generate unique lead ID."""
        
        timestamp = str(int(time.time()))
        email_hash = hashlib.md5(lead_data["email"].encode()).hexdigest()[:8]
        company_hash = hashlib.md5(lead_data["company"].encode()).hexdigest()[:6]
        
        return f"lead_{timestamp}_{email_hash}_{company_hash}"
    
    def generate_demo_token(self, lead_id: str, lead_data: Dict[str, Any]) -> str:
        """Generate demo token for lead."""
        
        token_data = f"{lead_id}:{lead_data['email']}:{int(time.time())}"
        token_hash = hashlib.sha256(token_data.encode()).hexdigest()
        
        return f"demo_{token_hash[:32]}"
    
    def store_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store lead information and generate demo token."""
        
        lead_id = self.generate_lead_id(lead_data)
        demo_token = self.generate_demo_token(lead_id, lead_data)
        
        # Calculate qualification
        qualification_score = self.calculate_qualification_score(lead_data)
        priority_level = self.determine_priority_level(qualification_score)
        estimated_value = self.estimate_value(qualification_score, lead_data.get("company_size", ""))
        
        # Store lead
        lead_info = {
            "lead_id": lead_id,
            "demo_token": demo_token,
            "email": lead_data["email"],
            "company": lead_data["company"],
            "use_case": lead_data["use_case"],
            "name": lead_data.get("name", ""),
            "phone": lead_data.get("phone", ""),
            "website": lead_data.get("website", ""),
            "job_title": lead_data.get("job_title", ""),
            "company_size": lead_data.get("company_size", ""),
            "industry": lead_data.get("industry", ""),
            "source": lead_data.get("source", ""),
            "campaign": lead_data.get("campaign", ""),
            "referrer": lead_data.get("referrer", ""),
            
            # Qualification metrics
            "qualification_score": qualification_score,
            "priority_level": priority_level,
            "estimated_value": estimated_value,
            
            # Demo tracking
            "captured_at": datetime.utcnow(),
            "attempt_count": 0,
            "last_attempt": None,
            "demo_token_expires_at": datetime.utcnow() + timedelta(hours=24),
            
            # Conversion tracking
            "converted": False,
            "conversion_date": None,
            "trial_started": False,
            "trial_start_date": None,
            
            # Engagement tracking
            "email_opened": False,
            "demo_completed": False,
            "paywall_hit": False,
            "follow_up_scheduled": False,
        }
        
        LEAD_STORAGE[lead_id] = lead_info
        DEMO_TOKENS[demo_token] = lead_id
        
        return lead_info
    
    def validate_demo_token(self, demo_token: str) -> Optional[Dict[str, Any]]:
        """Validate demo token and return lead info."""
        
        lead_id = DEMO_TOKENS.get(demo_token)
        if not lead_id:
            return None
        
        lead_info = LEAD_STORAGE.get(lead_id)
        if not lead_info:
            return None
        
        # Check token expiration
        if datetime.utcnow() > lead_info["demo_token_expires_at"]:
            # Token expired
            del DEMO_TOKENS[demo_token]
            return None
        
        return lead_info
    
    def increment_demo_attempt(self, demo_token: str) -> Dict[str, Any]:
        """Increment demo attempt count for lead."""
        
        lead_info = self.validate_demo_token(demo_token)
        if not lead_info:
            raise ValueError("Invalid demo token")
        
        lead_info["attempt_count"] += 1
        lead_info["last_attempt"] = datetime.utcnow()
        
        # Check if they hit the paywall
        if lead_info["attempt_count"] >= 3:
            lead_info["paywall_hit"] = True
        
        # Check if demo completed
        if lead_info["attempt_count"] >= 1:
            lead_info["demo_completed"] = True
        
        return lead_info
    
    def get_lead_analytics(self) -> Dict[str, Any]:
        """Get analytics dashboard for leads."""
        
        total_leads = len(LEAD_STORAGE)
        
        # Time-based filtering
        now = datetime.utcnow()
        today_leads = sum(
            1 for lead in LEAD_STORAGE.values()
            if lead["captured_at"].date() == now.date()
        )
        
        week_ago = now - timedelta(days=7)
        week_leads = sum(
            1 for lead in LEAD_STORAGE.values()
            if lead["captured_at"] > week_ago
        )
        
        # Conversion metrics
        converted_leads = sum(1 for lead in LEAD_STORAGE.values() if lead["converted"])
        conversion_rate = converted_leads / total_leads if total_leads > 0 else 0
        
        trial_started_leads = sum(1 for lead in LEAD_STORAGE.values() if lead["trial_started"])
        
        # Quality metrics
        qualification_scores = [lead["qualification_score"] for lead in LEAD_STORAGE.values()]
        avg_qualification_score = sum(qualification_scores) / len(qualification_scores) if qualification_scores else 0
        
        high_value_leads = sum(1 for lead in LEAD_STORAGE.values() if lead["estimated_value"] == "$10,000+")
        enterprise_leads = sum(1 for lead in LEAD_STORAGE.values() if lead.get("company_size") in ["501-1000", "1000+"])
        
        # Engagement metrics
        demo_completed_leads = sum(1 for lead in LEAD_STORAGE.values() if lead["demo_completed"])
        demo_completion_rate = demo_completed_leads / total_leads if total_leads > 0 else 0
        
        attempt_counts = [lead["attempt_count"] for lead in LEAD_STORAGE.values()]
        avg_demo_attempts = sum(attempt_counts) / len(attempt_counts) if attempt_counts else 0
        
        paywall_hit_leads = sum(1 for lead in LEAD_STORAGE.values() if lead["paywall_hit"])
        paywall_hit_rate = paywall_hit_leads / total_leads if total_leads > 0 else 0
        
        # Time to conversion
        conversion_times = []
        for lead in LEAD_STORAGE.values():
            if lead["converted"] and lead["conversion_date"]:
                conversion_time = (lead["conversion_date"] - lead["captured_at"]).days
                conversion_times.append(conversion_time)
        
        avg_time_to_conversion = sum(conversion_times) / len(conversion_times) if conversion_times else 0
        
        # Top segments
        industries = {}
        use_cases = {}
        company_sizes = {}
        
        for lead in LEAD_STORAGE.values():
            # Industry breakdown
            industry = lead.get("industry", "other")
            industries[industry] = industries.get(industry, 0) + 1
            
            # Use case breakdown
            use_case = lead.get("use_case", "other")
            use_cases[use_case] = use_cases.get(use_case, 0) + 1
            
            # Company size breakdown
            size = lead.get("company_size", "unknown")
            company_sizes[size] = company_sizes.get(size, 0) + 1
        
        # Sort by count
        top_industries = sorted(industries.items(), key=lambda x: x[1], reverse=True)[:5]
        top_use_cases = sorted(use_cases.items(), key=lambda x: x[1], reverse=True)[:5]
        top_company_sizes = sorted(company_sizes.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_leads": total_leads,
            "new_leads_today": today_leads,
            "new_leads_this_week": week_leads,
            "conversion_rate": conversion_rate,
            
            "avg_qualification_score": avg_qualification_score,
            "high_value_leads": high_value_leads,
            "enterprise_leads": enterprise_leads,
            
            "demo_completion_rate": demo_completion_rate,
            "avg_demo_attempts": avg_demo_attempts,
            "paywall_hit_rate": paywall_hit_rate,
            
            "trials_started": trial_started_leads,
            "trials_converted": converted_leads,
            "time_to_conversion_days": avg_time_to_conversion,
            
            "top_industries": [{"industry": k, "count": v} for k, v in top_industries],
            "top_use_cases": [{"use_case": k, "count": v} for k, v in top_use_cases],
            "top_company_sizes": [{"size": k, "count": v} for k, v in top_company_sizes],
        }


# Initialize lead manager
lead_manager = LeadManager()


@router.post("/capture", response_model=LeadCaptureResponse)
async def capture_lead(request: LeadCaptureRequest):
    """
    Capture lead information and generate demo token.
    
    This is the required first step before any demo execution.
    Returns a demo token that enables 3 free executions with escalating value.
    """
    
    try:
        # Validate required fields
        if not request.email or not request.company or not request.use_case:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required fields: email, company, use_case"
            )
        
        # Check for duplicate email
        existing_lead = next(
            (lead for lead in LEAD_STORAGE.values() if lead["email"] == request.email),
            None
        )
        
        if existing_lead:
            # Return existing demo token if still valid
            if datetime.utcnow() < existing_lead["demo_token_expires_at"]:
                return LeadCaptureResponse(
                    lead_id=existing_lead["lead_id"],
                    demo_token=existing_lead["demo_token"],
                    message="Welcome back! Your existing demo token is still active.",
                    demo_attempts_remaining=3 - existing_lead["attempt_count"],
                    demo_endpoints=["/api/v1/ai/execute", "/ai/execute"],
                    next_steps=[
                        f"Use your demo token for {3 - existing_lead['attempt_count']} more attempts",
                        "Each attempt provides escalating value",
                        "Upgrade after 3 attempts for full access"
                    ],
                    qualification_score=existing_lead["qualification_score"],
                    estimated_value=existing_lead["estimated_value"],
                    priority_level=existing_lead["priority_level"],
                    follow_up_scheduled=existing_lead["follow_up_scheduled"],
                    demo_expiry_hours=int((existing_lead["demo_token_expires_at"] - datetime.utcnow()).total_seconds() / 3600)
                )
            else:
                # Token expired, create new one
                pass
        
        # Store lead and generate token
        lead_data = request.dict()
        lead_info = lead_manager.store_lead(lead_data)
        
        return LeadCaptureResponse(
            lead_id=lead_info["lead_id"],
            demo_token=lead_info["demo_token"],
            message="Lead captured successfully. You can now execute demo operations.",
            demo_attempts_remaining=3,
            demo_endpoints=["/api/v1/ai/execute", "/ai/execute"],
            next_steps=[
                "Use demo_token in requests to demo endpoints",
                "Each attempt provides escalating value",
                "After 3 attempts, upgrade to continue"
            ],
            qualification_score=lead_info["qualification_score"],
            estimated_value=lead_info["estimated_value"],
            priority_level=lead_info["priority_level"],
            follow_up_scheduled=False,  # Would integrate with CRM
            demo_expiry_hours=24
        )
        
    except Exception as e:
        logger.error(f"Lead capture failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lead capture failed"
        )


@router.get("/status/{demo_token}", response_model=LeadStatusResponse)
async def get_lead_status(demo_token: str):
    """Get lead status and demo usage information."""
    
    lead_info = lead_manager.validate_demo_token(demo_token)
    if not lead_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired demo token"
        )
    
    # Determine engagement level
    if lead_info["attempt_count"] >= 3:
        engagement_level = "high"
    elif lead_info["attempt_count"] >= 1:
        engagement_level = "medium"
    else:
        engagement_level = "low"
    
    # Calculate conversion probability (simple heuristic)
    base_probability = lead_info["qualification_score"]
    if lead_info["paywall_hit"]:
        base_probability += 0.2  # Hit paywall = more interested
    if lead_info["demo_completed"]:
        base_probability += 0.1  # Completed demo = more engaged
    
    conversion_probability = min(base_probability, 1.0)
    
    # Determine token status
    if datetime.utcnow() > lead_info["demo_token_expires_at"]:
        token_status = "expired"
    elif lead_info["attempt_count"] >= 3:
        token_status = "used_up"
    else:
        token_status = "active"
    
    # Recommended next step
    if token_status == "expired":
        next_step = "Re-request demo token"
    elif lead_info["attempt_count"] >= 3:
        next_step = "Upgrade to paid plan"
    elif lead_info["attempt_count"] == 0:
        next_step = "Try first demo execution"
    else:
        next_step = f"Continue demo ({3 - lead_info['attempt_count']} attempts remaining)"
    
    return LeadStatusResponse(
        lead_id=lead_info["lead_id"],
        email=lead_info["email"],
        company=lead_info["company"],
        demo_attempts_used=lead_info["attempt_count"],
        demo_attempts_remaining=max(0, 3 - lead_info["attempt_count"]),
        demo_token_status=token_status,
        qualification_score=lead_info["qualification_score"],
        engagement_level=engagement_level,
        conversion_probability=conversion_probability,
        captured_at=lead_info["captured_at"],
        last_demo_attempt=lead_info["last_attempt"],
        demo_token_expires_at=lead_info["demo_token_expires_at"],
        recommended_next_step=next_step,
        upgrade_incentives={
            "limited_time": "20% off first month" if lead_info["priority_level"] == "high" else "10% off first month",
            "demo_value": "$1,247 in value demonstrated",
            "roi_guarantee": "30-day money-back guarantee",
            "priority_support": lead_info["priority_level"] == "high",
        }
    )


@router.get("/analytics", response_model=LeadAnalyticsResponse)
async def get_lead_analytics():
    """Get analytics dashboard for lead performance."""
    
    analytics = lead_manager.get_lead_analytics()
    
    return LeadAnalyticsResponse(
        total_leads=analytics["total_leads"],
        new_leads_today=analytics["new_leads_today"],
        new_leads_this_week=analytics["new_leads_this_week"],
        conversion_rate=analytics["conversion_rate"],
        avg_qualification_score=analytics["avg_qualification_score"],
        high_value_leads=analytics["high_value_leads"],
        enterprise_leads=analytics["enterprise_leads"],
        demo_completion_rate=analytics["demo_completion_rate"],
        avg_demo_attempts=analytics["avg_demo_attempts"],
        paywall_hit_rate=analytics["paywall_hit_rate"],
        trials_started=analytics["trials_started"],
        trials_converted=analytics["trials_converted"],
        time_to_conversion_days=analytics["time_to_conversion_days"],
        top_industries=analytics["top_industries"],
        top_use_cases=analytics["top_use_cases"],
        top_company_sizes=analytics["top_company_sizes"]
    )


@router.post("/convert")
async def mark_lead_converted(demo_token: str):
    """Mark lead as converted (called after successful upgrade)."""
    
    lead_info = lead_manager.validate_demo_token(demo_token)
    if not lead_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired demo token"
        )
    
    lead_info["converted"] = True
    lead_info["conversion_date"] = datetime.utcnow()
    
    return {
        "message": "Lead marked as converted",
        "lead_id": lead_info["lead_id"],
        "conversion_date": lead_info["conversion_date"]
    }


@router.post("/trial-start")
async def start_trial(demo_token: str):
    """Mark lead as trial started."""
    
    lead_info = lead_manager.validate_demo_token(demo_token)
    if not lead_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired demo token"
        )
    
    lead_info["trial_started"] = True
    lead_info["trial_start_date"] = datetime.utcnow()
    
    return {
        "message": "Trial started",
        "lead_id": lead_info["lead_id"],
        "trial_start_date": lead_info["trial_start_date"]
    }
