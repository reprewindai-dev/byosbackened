"""VCTT-AGI Engine API endpoints."""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, Optional
from core.vctt_agi.engine import vctt_engine, VcttSessionRequest, VcttSessionResponse

router = APIRouter(prefix="/vctt", tags=["vctt-agi"])


@router.post("/session/start", response_model=str)
async def start_session(request: VcttSessionRequest) -> str:
    """Start a new VCTT coherence session."""
    try:
        session_id = await vctt_engine.start_session(request)
        return session_id
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start VCTT session: {str(e)}")


@router.post("/session/step", response_model=VcttSessionResponse)
async def step_session(session_id: str) -> VcttSessionResponse:
    """Execute one step in the VCTT coherence process."""
    try:
        response = await vctt_engine.step_session(session_id)
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VCTT step failed: {str(e)}")


@router.get("/session/{session_id}")
async def get_session(session_id: str) -> Dict[str, Any]:
    """Get VCTT session state."""
    session = vctt_engine.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return {
        "session_id": session.session_id,
        "mode": session.mode.value,
        "step_count": session.step_count,
        "max_steps": session.max_steps,
        "tau_min": session.tau_min,
        "repair_used": session.repair_used,
        "converged": session.converged,
        "agent_responses_count": len(session.agent_responses),
        "coherence_history_count": len(session.coherence_history),
        "final_response": session.final_response,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat()
    }


@router.get("/sessions")
async def list_sessions() -> Dict[str, Any]:
    """List all active VCTT sessions."""
    sessions = {}
    for session_id, session in vctt_engine.sessions.items():
        sessions[session_id] = {
            "mode": session.mode.value,
            "step_count": session.step_count,
            "converged": session.converged,
            "tau_current": session.coherence_history[-1].tau if session.coherence_history else None,
            "created_at": session.created_at.isoformat()
        }

    return {
        "total_sessions": len(sessions),
        "sessions": sessions
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str) -> Dict[str, str]:
    """Delete a VCTT session."""
    if session_id not in vctt_engine.sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    del vctt_engine.sessions[session_id]
    return {"status": "deleted", "session_id": session_id}


@router.get("/health")
async def vctt_health() -> Dict[str, Any]:
    """VCTT-AGI Engine health check."""
    return {
        "status": "healthy",
        "engine": "VCTT-AGI",
        "version": "1.0.0",
        "active_sessions": len(vctt_engine.sessions),
        "agents": [role.value for role in ["analyst", "relational", "ethics", "synthesiser"]],
        "capabilities": ["coherence_analysis", "self_repair", "trust_scoring"]
    }


@router.post("/analyze-coherence")
async def analyze_coherence(text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Quick coherence analysis without creating a persistent session."""
    try:
        if context is None:
            context = {}

        # Run a quick analysis with all agents
        responses = []
        for role in ["analyst", "relational", "ethics", "synthesiser"]:
            # Mock agent responses for quick analysis
            response = f"{role.title()} analysis of: {text[:50]}..."
            responses.append({
                "agent": role,
                "response": response,
                "confidence": 0.8,
                "reasoning": f"{role.title()} perspective applied"
            })

        # Mock coherence metrics
        coherence = {
            "tension": 0.2,
            "uncertainty": 0.15,
            "contradiction": 0.1,
            "tau": 0.775  # 1 - (0.4*0.2 + 0.3*0.15 + 0.3*0.1)
        }

        return {
            "input_text": text,
            "agent_responses": responses,
            "coherence_metrics": coherence,
            "assessment": "High coherence" if coherence["tau"] > 0.8 else "Moderate coherence" if coherence["tau"] > 0.6 else "Low coherence"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Coherence analysis failed: {str(e)}")
