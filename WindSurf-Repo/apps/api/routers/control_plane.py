"""Unified AI Execution Control Plane API - Enterprise AI Governance Platform."""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
from datetime import datetime
from core.control_plane.engine import control_plane, RunRequest, RunResult, RunStatus, PolicyProfile, OutputSchema

router = APIRouter(prefix="/control-plane", tags=["control-plane"])


# ===== RUN MANAGEMENT =====

@router.post("/runs", response_model=RunResult)
async def create_run(request: RunRequest, background_tasks: BackgroundTasks) -> RunResult:
    """Create a new governed AI run through the unified control plane."""
    try:
        run_result = await control_plane.create_run(request)
        return run_result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create run: {str(e)}")


@router.get("/runs/{run_id}", response_model=RunResult)
async def get_run(run_id: str) -> RunResult:
    """Get run details and status."""
    run = control_plane.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run


@router.get("/runs", response_model=List[RunResult])
async def list_runs(
    status: Optional[RunStatus] = Query(None, description="Filter by run status"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of runs to return")
) -> List[RunResult]:
    """List runs with optional filtering."""
    return control_plane.list_runs(status, limit)


@router.get("/runs/{run_id}/events")
async def get_run_events(
    run_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return")
) -> Dict[str, Any]:
    """Get event stream for a specific run."""
    events = control_plane.get_events(run_id, limit)
    return {
        "run_id": run_id,
        "events": [event.dict() for event in events],
        "total_events": len(events)
    }


@router.get("/events")
async def get_all_events(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return")
) -> Dict[str, Any]:
    """Get global event stream across all runs."""
    events = control_plane.get_events(None, limit)
    return {
        "events": [event.dict() for event in events],
        "total_events": len(events)
    }


# ===== POLICY MANAGEMENT =====

@router.post("/policies", response_model=PolicyProfile)
async def create_policy_profile(profile: PolicyProfile) -> PolicyProfile:
    """Create a new governance policy profile."""
    try:
        return control_plane.create_policy_profile(profile)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create policy: {str(e)}")


@router.get("/policies/{policy_id}", response_model=PolicyProfile)
async def get_policy_profile(policy_id: str) -> PolicyProfile:
    """Get policy profile by ID."""
    policy = control_plane.get_policy_profile(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")
    return policy


@router.get("/policies", response_model=List[PolicyProfile])
async def list_policy_profiles() -> List[PolicyProfile]:
    """List all policy profiles."""
    return control_plane.list_policy_profiles()


@router.put("/policies/{policy_id}/approve")
async def approve_policy_version(
    policy_id: str,
    version: int = Query(..., ge=1, description="Policy version to approve"),
    approver_notes: Optional[str] = Query(None, description="Optional approval notes")
) -> Dict[str, Any]:
    """Approve a policy version for production use (4-eyes control)."""
    policy = control_plane.get_policy_profile(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")

    if policy.version != version:
        raise HTTPException(status_code=400, detail=f"Policy version mismatch: requested {version}, current {policy.version}")

    if policy.status == "approved":
        raise HTTPException(status_code=409, detail="Policy version already approved")

    # Mock approval process - in real implementation would require authentication
    policy.status = "approved"
    policy.updated_at = datetime.utcnow()

    return {
        "policy_id": policy_id,
        "version": version,
        "status": "approved",
        "approved_at": policy.updated_at.isoformat(),
        "approver_notes": approver_notes
    }


# ===== SCHEMA MANAGEMENT =====

@router.post("/schemas", response_model=OutputSchema)
async def create_output_schema(schema: OutputSchema) -> OutputSchema:
    """Create a new output schema for validation."""
    try:
        return control_plane.create_output_schema(schema)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create schema: {str(e)}")


@router.get("/schemas/{schema_id}", response_model=OutputSchema)
async def get_output_schema(schema_id: str) -> OutputSchema:
    """Get output schema by ID."""
    schema = control_plane.get_output_schema(schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail=f"Schema {schema_id} not found")
    return schema


@router.get("/schemas", response_model=List[OutputSchema])
async def list_output_schemas() -> List[OutputSchema]:
    """List all output schemas."""
    return control_plane.list_output_schemas()


# ===== TELEMETRY & ANALYTICS =====

@router.get("/telemetry/summary")
async def get_telemetry_summary() -> Dict[str, Any]:
    """Get comprehensive governance telemetry summary."""
    runs = control_plane.list_runs(limit=1000)

    total_runs = len(runs)
    completed_runs = len([r for r in runs if r.status == RunStatus.COMPLETED])
    failed_runs = len([r for r in runs if r.status == RunStatus.FAILED])
    blocked_runs = len([r for r in runs if r.status == RunStatus.BLOCKED])

    # Calculate governance metrics
    tier0_runs = len([r for r in runs if r.governance.get("escalation_level") == 0])
    tier1_runs = len([r for r in runs if r.governance.get("escalation_level") == 1])
    tier2_runs = len([r for r in runs if r.governance.get("escalation_level") == 2])

    # Calculate coherence metrics
    runs_with_coherence = [r for r in runs if r.coherence]
    avg_tau = sum(r.coherence["tau"] for r in runs_with_coherence) / len(runs_with_coherence) if runs_with_coherence else 0

    # Calculate convergence metrics
    converged_runs = len([r for r in runs if r.convergence.get("converged")])
    avg_quality = sum(r.convergence.get("quality_score", 0) for r in runs if r.convergence) / len([r for r in runs if r.convergence]) if any(r.convergence for r in runs) else 0

    return {
        "summary": {
            "total_runs": total_runs,
            "completed_runs": completed_runs,
            "failed_runs": failed_runs,
            "blocked_runs": blocked_runs,
            "success_rate": completed_runs / total_runs if total_runs > 0 else 0
        },
        "governance": {
            "tier0_runs": tier0_runs,
            "tier1_runs": tier1_runs,
            "tier2_runs": tier2_runs,
            "escalation_distribution": {
                "normal": tier0_runs,
                "enhanced_validation": tier1_runs,
                "maximum_governance": tier2_runs
            }
        },
        "coherence": {
            "runs_with_coherence": len(runs_with_coherence),
            "average_tau": round(avg_tau, 3),
            "coherence_adoption_rate": len(runs_with_coherence) / total_runs if total_runs > 0 else 0
        },
        "convergence": {
            "converged_runs": converged_runs,
            "average_quality_score": round(avg_quality, 3),
            "convergence_rate": converged_runs / completed_runs if completed_runs > 0 else 0
        },
        "routing": {
            "providers_used": list(set(r.routing.get("provider") for r in runs if r.routing)),
            "regions_used": list(set(r.routing.get("region") for r in runs if r.routing)),
            "cost_savings_estimated": sum(r.routing.get("estimated_cost_usd", 0) for r in runs if r.routing)
        }
    }


@router.get("/telemetry/governance")
async def get_governance_telemetry() -> Dict[str, Any]:
    """Get detailed governance telemetry."""
    runs = control_plane.list_runs(limit=1000)

    governance_data = []
    for run in runs:
        if run.governance:
            governance_data.append({
                "run_id": run.run_id,
                "escalation_level": run.governance.get("escalation_level"),
                "detrimental_score": run.governance.get("detrimental_score"),
                "fracture_score": run.governance.get("fracture_score"),
                "structural_integrity": run.governance.get("structural_integrity"),
                "watchtower_validations": run.governance.get("watchtower_validations"),
                "status": run.status.value,
                "created_at": run.created_at.isoformat()
            })

    return {
        "governance_telemetry": governance_data,
        "total_runs_analyzed": len(governance_data)
    }


@router.get("/telemetry/coherence")
async def get_coherence_telemetry() -> Dict[str, Any]:
    """Get VCTT coherence telemetry."""
    runs = control_plane.list_runs(limit=1000)

    coherence_data = []
    for run in runs:
        if run.coherence:
            coherence_data.append({
                "run_id": run.run_id,
                "session_id": run.coherence.get("session_id"),
                "mode": run.coherence.get("mode"),
                "tau": run.coherence.get("tau"),
                "tension": run.coherence.get("tension"),
                "uncertainty": run.coherence.get("uncertainty"),
                "contradiction": run.coherence.get("contradiction"),
                "repair_used": run.coherence.get("repair_used"),
                "steps_used": run.coherence.get("steps_used"),
                "status": run.status.value
            })

    return {
        "coherence_telemetry": coherence_data,
        "total_runs_with_coherence": len(coherence_data)
    }


# ===== SYSTEM HEALTH =====

@router.get("/health")
async def control_plane_health() -> Dict[str, Any]:
    """Unified Control Plane health check."""
    return {
        "status": "healthy",
        "service": "Unified AI Execution Control Plane",
        "version": "1.0.0",
        "components": {
            "policy_profiles": len(control_plane.policy_profiles),
            "output_schemas": len(control_plane.output_schemas),
            "active_runs": len(control_plane.active_runs),
            "event_stream_size": len(control_plane.event_stream)
        },
        "capabilities": [
            "cognitive_governance",
            "deterministic_outputs",
            "resource_accountability",
            "real_time_visibility",
            "escalation_tiers",
            "approval_workflows",
            "comprehensive_telemetry"
        ],
        "governance_layers": [
            "Seked (Cognitive Control)",
            "VCTT (Inner Coherence)",
            "ConvergeOS (Output Determinism)",
            "ECOBE (Resource Routing)"
        ]
    }


@router.get("/capabilities")
async def get_capabilities() -> Dict[str, Any]:
    """Get control plane capabilities and supported features."""
    return {
        "governance": {
            "cognitive_control": "Seked-based escalation tiers and policy enforcement",
            "coherence_analysis": "VCTT multi-agent trust scoring and repair loops",
            "structural_integrity": "Continuous fracture and detrimental monitoring",
            "approval_workflows": "4-eyes principle for critical policy changes"
        },
        "execution": {
            "deterministic_outputs": "ConvergeOS schema validation and retry logic",
            "multi_provider_support": ["openai", "anthropic", "google", "azure", "bedrock"],
            "resource_optimization": "ECOBE carbon/latency/cost balancing",
            "real_time_routing": "Dynamic provider and region selection"
        },
        "observability": {
            "event_streaming": "Complete audit trail for all governance decisions",
            "telemetry_aggregation": "Real-time metrics on coherence, convergence, and routing",
            "escalation_tracking": "Tier-based governance level monitoring",
            "performance_metrics": "Quality scores, processing times, and cost tracking"
        },
        "security": {
            "risk_containment": "Automatic blocking of high-risk requests",
            "policy_boundaries": "Granular controls on model access and data handling",
            "audit_compliance": "Complete traceability for regulatory requirements",
            "data_protection": "PII detection and handling controls"
        }
    }
