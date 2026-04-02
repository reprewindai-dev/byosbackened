"""Unified AI Execution Control Plane - Enterprise AI Governance Platform."""
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, validator
import uuid
import asyncio
import logging

logger = logging.getLogger(__name__)


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class EscalationLevel(int, Enum):
    TIER_0 = 0  # Normal processing
    TIER_1 = 1  # Enhanced validation
    TIER_2 = 2  # Maximum governance + approval required


class ProviderType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    META = "meta"
    AZURE_OPENAI = "azure_openai"
    BEDROCK = "bedrock"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyProfile(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    version: int = 1
    status: str = "draft"  # draft, approved, deprecated

    # Seked governance settings
    seked: Dict[str, Any] = Field(default_factory=dict)
    # VCTT coherence settings
    vctt: Dict[str, Any] = Field(default_factory=dict)
    # ConvergeOS output control
    converge: Dict[str, Any] = Field(default_factory=dict)
    # ECOBE routing settings
    ecobe: Dict[str, Any] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class OutputSchema(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    version: int = 1
    json_schema: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RunRequest(BaseModel):
    request_id: Optional[str] = None
    policy_profile_id: str
    schema_id: str
    task: Dict[str, Any]
    inputs: Dict[str, Any]
    constraints: Dict[str, Any] = Field(default_factory=dict)
    execution: Dict[str, Any] = Field(default_factory=dict)

    @validator('request_id', pre=True, always=True)
    def set_request_id(cls, v):
        return v or str(uuid.uuid4())


class RunResult(BaseModel):
    run_id: str
    status: RunStatus
    created_at: datetime
    completed_at: Optional[datetime] = None

    # Governance assessment
    governance: Dict[str, Any] = Field(default_factory=dict)

    # VCTT coherence data
    coherence: Optional[Dict[str, Any]] = None

    # Final output
    result: Optional[Dict[str, Any]] = None

    # Execution details
    routing: Dict[str, Any] = Field(default_factory=dict)
    convergence: Dict[str, Any] = Field(default_factory=dict)

    # Error details
    error: Optional[Dict[str, Any]] = None


class ControlPlaneEvent(BaseModel):
    event_type: str
    run_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any]


class UnifiedControlPlane:
    """Unified AI Execution Control Plane - Enterprise AI Governance Platform."""

    def __init__(self):
        self.policy_profiles: Dict[str, PolicyProfile] = {}
        self.output_schemas: Dict[str, OutputSchema] = {}
        self.active_runs: Dict[str, RunResult] = {}
        self.event_stream: List[ControlPlaneEvent] = []

        # Initialize with default components
        self._initialize_default_profiles()
        self._initialize_default_schemas()

    def _initialize_default_profiles(self):
        """Initialize default policy profiles."""
        default_profile = PolicyProfile(
            id="default_policy",
            name="Default Governance Profile",
            description="Standard governance profile for general AI tasks",
            seked={
                "escalation_thresholds": {
                    "tier0": {"detrimental_max": 0.2, "fracture_max": 0.15},
                    "tier1": {"detrimental_max": 0.4, "fracture_max": 0.3},
                    "tier2": {"detrimental_max": 0.6, "fracture_max": 0.5}
                },
                "max_tier2_per_minute": 10
            },
            vctt={
                "enabled": True,
                "tau_min": 0.75,
                "max_steps": 5,
                "force_repair_on_tier2": True
            },
            converge={
                "max_attempts": 3,
                "quality_threshold": 0.8,
                "hard_fail_on_schema": True
            },
            ecobe={
                "carbon_mode": "minimize",
                "weights": {"carbon": 0.4, "latency": 0.3, "cost": 0.3},
                "provider_allowlist": ["openai", "anthropic", "google"],
                "region_allowlist": ["us-east-1", "us-west-2", "eu-west-1"]
            }
        )
        self.policy_profiles[default_profile.id] = default_profile

    def _initialize_default_schemas(self):
        """Initialize default output schemas."""
        default_schema = OutputSchema(
            id="default_response",
            name="Default Response Schema",
            description="Generic response schema for AI outputs",
            json_schema={
                "type": "object",
                "properties": {
                    "response": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "metadata": {"type": "object"}
                },
                "required": ["response"]
            }
        )
        self.output_schemas[default_schema.id] = default_schema

    def _compute_escalation_level(self, detrimental_score: float, fracture_score: float,
                                 policy: PolicyProfile) -> EscalationLevel:
        """Compute escalation level based on governance scores."""
        thresholds = policy.seked.get("escalation_thresholds", {})

        if (detrimental_score >= thresholds.get("tier2", {}).get("detrimental_max", 0.6) or
            fracture_score >= thresholds.get("tier2", {}).get("fracture_max", 0.5)):
            return EscalationLevel.TIER_2

        if (detrimental_score >= thresholds.get("tier1", {}).get("detrimental_max", 0.4) or
            fracture_score >= thresholds.get("tier1", {}).get("fracture_max", 0.3)):
            return EscalationLevel.TIER_1

        return EscalationLevel.TIER_0

    def _assess_governance(self, request: RunRequest) -> Dict[str, Any]:
        """Perform comprehensive governance assessment."""
        # Mock governance assessment - in real implementation would use Seked components
        detrimental_score = 0.15  # Mock shadow tracking score
        fracture_score = 0.08     # Mock structural integrity score

        policy = self.policy_profiles.get(request.policy_profile_id)
        if not policy:
            raise ValueError(f"Policy profile {request.policy_profile_id} not found")

        escalation_level = self._compute_escalation_level(
            detrimental_score, fracture_score, policy
        )

        return {
            "escalation_level": escalation_level.value,
            "detrimental_score": detrimental_score,
            "fracture_score": fracture_score,
            "structural_integrity": 0.92,  # Mock value
            "watchtower_validations": 3,
            "shadow_forces_detected": 0,
            "policy_compliant": True
        }

    def _execute_vctt_coherence(self, run_id: str, request: RunRequest,
                               governance: Dict[str, Any]) -> Dict[str, Any]:
        """Execute VCTT coherence analysis."""
        # Mock VCTT execution - in real implementation would call VCTT engine
        escalation_level = governance["escalation_level"]

        # Adjust mode based on escalation
        mode = "normal"
        if escalation_level >= 2:
            mode = "slow_down"
        elif escalation_level >= 1:
            mode = "clarify"

        # Mock coherence metrics
        coherence = {
            "session_id": f"vctt_{run_id}",
            "mode": mode,
            "tau": 0.82,
            "tension": 0.12,
            "uncertainty": 0.08,
            "contradiction": 0.06,
            "repair_used": escalation_level >= 1,
            "steps_used": 3,
            "kernel_version": "1.0.0"
        }

        return coherence

    def _execute_convergeos(self, run_id: str, schema_id: str,
                           raw_output: str) -> Dict[str, Any]:
        """Execute ConvergeOS deterministic output control."""
        schema = self.output_schemas.get(schema_id)
        if not schema:
            raise ValueError(f"Output schema {schema_id} not found")

        # Mock convergence - in real implementation would validate against schema
        convergence = {
            "attempts": 1,
            "quality_score": 0.94,
            "converged": True,
            "schema_valid": True,
            "validated_output": {
                "response": raw_output,
                "confidence": 0.88,
                "metadata": {"processing_time_ms": 1250}
            }
        }

        return convergence

    def _execute_ecobe_routing(self, request: RunRequest) -> Dict[str, Any]:
        """Execute ECOBE resource-optimized routing."""
        policy = self.policy_profiles.get(request.policy_profile_id)

        # Mock routing decision - in real implementation would optimize based on constraints
        routing = {
            "provider": "openai",
            "region": "us-west-2",
            "model": "gpt-4",
            "carbon_intensity_gco2_kwh": 245.0,
            "estimated_cost_usd": 0.023,
            "estimated_latency_ms": 1250,
            "routing_reason": "Balanced carbon/latency/cost optimization"
        }

        # Apply policy constraints
        if policy and policy.ecobe.get("region_allowlist"):
            allowed_regions = policy.ecobe["region_allowlist"]
            if routing["region"] not in allowed_regions:
                routing["region"] = allowed_regions[0]
                routing["routing_reason"] = f"Constrained to allowed region: {allowed_regions[0]}"

        return routing

    def _should_block_run(self, governance: Dict[str, Any], policy: PolicyProfile) -> bool:
        """Determine if run should be blocked based on governance assessment."""
        escalation_level = governance["escalation_level"]

        # Block Tier 2 escalations unless explicitly allowed
        if escalation_level >= 2:
            return not policy.seked.get("allow_tier2_automatic", False)

        return False

    async def create_run(self, request: RunRequest) -> RunResult:
        """Create and initiate a governed AI run."""
        run_id = str(uuid.uuid4())

        # Get policy and validate
        policy = self.policy_profiles.get(request.policy_profile_id)
        if not policy:
            raise ValueError(f"Policy profile {request.policy_profile_id} not found")

        # Assess governance
        governance = self._assess_governance(request)

        # Check if run should be blocked
        if self._should_block_run(governance, policy):
            run = RunResult(
                run_id=run_id,
                status=RunStatus.BLOCKED,
                created_at=datetime.utcnow(),
                governance=governance,
                error={
                    "code": "GOVERNANCE_BLOCK",
                    "message": "Run blocked by governance policy",
                    "details": {"escalation_level": governance["escalation_level"]}
                }
            )
            self.active_runs[run_id] = run
            self._emit_event("RUN_BLOCKED", run_id, {"reason": "governance_policy"})
            return run

        # Create run record
        run = RunResult(
            run_id=run_id,
            status=RunStatus.QUEUED,
            created_at=datetime.utcnow(),
            governance=governance
        )
        self.active_runs[run_id] = run

        self._emit_event("RUN_CREATED", run_id, {"request_id": request.request_id})
        self._emit_event("POLICY_EVALUATED", run_id, governance)

        # Start async processing
        asyncio.create_task(self._process_run(run_id, request))

        return run

    async def _process_run(self, run_id: str, request: RunRequest):
        """Process a run through the governance pipeline."""
        run = self.active_runs[run_id]
        run.status = RunStatus.RUNNING
        self._emit_event("RUN_RUNNING", run_id, {})

        try:
            # Phase 1: VCTT Coherence (if enabled)
            policy = self.policy_profiles[request.policy_profile_id]
            if policy.vctt.get("enabled", True):
                coherence = self._execute_vctt_coherence(run_id, request, run.governance)
                run.coherence = coherence
                self._emit_event("VCTT_SESSION_STARTED", run_id, {"session_id": coherence["session_id"]})
                self._emit_event("VCTT_STEPPED", run_id, coherence)

            # Phase 2: ECOBE Routing
            routing = self._execute_ecobe_routing(request)
            run.routing = routing
            self._emit_event("ECOBE_ROUTED", run_id, routing)

            # Phase 3: Execute AI request (mock)
            raw_output = f"Processed: {request.inputs.get('prompt', 'No prompt provided')}"
            self._emit_event("AI_EXECUTED", run_id, {"provider": routing["provider"]})

            # Phase 4: ConvergeOS Validation
            convergence = self._execute_convergeos(run_id, request.schema_id, raw_output)
            run.convergence = convergence
            self._emit_event("CONVERGE_ATTEMPTED", run_id, convergence)

            # Phase 5: Finalize
            run.result = convergence["validated_output"]
            run.status = RunStatus.COMPLETED
            run.completed_at = datetime.utcnow()

            self._emit_event("RUN_COMPLETED", run_id, {
                "quality_score": convergence["quality_score"],
                "processing_time_ms": (run.completed_at - run.created_at).total_seconds() * 1000
            })

        except Exception as e:
            logger.error(f"Run {run_id} failed: {e}")
            run.status = RunStatus.FAILED
            run.error = {
                "code": "PROCESSING_ERROR",
                "message": str(e),
                "details": {}
            }
            self._emit_event("RUN_FAILED", run_id, {"error": str(e)})

    def get_run(self, run_id: str) -> Optional[RunResult]:
        """Get run result by ID."""
        return self.active_runs.get(run_id)

    def list_runs(self, status: Optional[RunStatus] = None, limit: int = 50) -> List[RunResult]:
        """List runs with optional filtering."""
        runs = list(self.active_runs.values())

        if status:
            runs = [r for r in runs if r.status == status]

        # Sort by creation time, most recent first
        runs.sort(key=lambda r: r.created_at, reverse=True)

        return runs[:limit]

    def get_events(self, run_id: Optional[str] = None, limit: int = 100) -> List[ControlPlaneEvent]:
        """Get events for a run or all events."""
        events = self.event_stream

        if run_id:
            events = [e for e in events if e.run_id == run_id]

        # Sort by timestamp, most recent first
        events.sort(key=lambda e: e.timestamp, reverse=True)

        return events[:limit]

    def _emit_event(self, event_type: str, run_id: str, data: Dict[str, Any]):
        """Emit a control plane event."""
        event = ControlPlaneEvent(
            event_type=event_type,
            run_id=run_id,
            data=data
        )
        self.event_stream.append(event)

        # Keep only last 1000 events
        if len(self.event_stream) > 1000:
            self.event_stream = self.event_stream[-1000:]

    # Policy Management
    def create_policy_profile(self, profile: PolicyProfile) -> PolicyProfile:
        """Create a new policy profile."""
        if profile.id in self.policy_profiles:
            raise ValueError(f"Policy profile {profile.id} already exists")

        profile.created_at = datetime.utcnow()
        profile.updated_at = datetime.utcnow()
        self.policy_profiles[profile.id] = profile
        return profile

    def get_policy_profile(self, policy_id: str) -> Optional[PolicyProfile]:
        """Get policy profile by ID."""
        return self.policy_profiles.get(policy_id)

    def list_policy_profiles(self) -> List[PolicyProfile]:
        """List all policy profiles."""
        return list(self.policy_profiles.values())

    # Schema Management
    def create_output_schema(self, schema: OutputSchema) -> OutputSchema:
        """Create a new output schema."""
        if schema.id in self.output_schemas:
            raise ValueError(f"Output schema {schema.id} already exists")

        schema.created_at = datetime.utcnow()
        schema.updated_at = datetime.utcnow()
        self.output_schemas[schema.id] = schema
        return schema

    def get_output_schema(self, schema_id: str) -> Optional[OutputSchema]:
        """Get output schema by ID."""
        return self.output_schemas.get(schema_id)

    def list_output_schemas(self) -> List[OutputSchema]:
        """List all output schemas."""
        return list(self.output_schemas.values())


# Global control plane instance
control_plane = UnifiedControlPlane()


class ControlPlaneEngine:
    """Control plane engine for governance events."""
    
    async def log_governance_event(self, event_type: str, **kwargs):
        """Log a governance event."""
        pass


control_plane_engine = ControlPlaneEngine()
