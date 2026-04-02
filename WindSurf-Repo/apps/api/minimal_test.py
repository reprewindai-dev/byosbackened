"""Minimal BYOS API for testing - bypasses heavy middleware."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="BYOS Test API", version="0.1.0")

@app.get("/health")
async def health():
    """Simple health check."""
    return {"status": "ok", "version": "0.1.0"}

@app.get("/api/v1/health")
async def health_v1():
    """API health check."""
    return {"status": "ok", "version": "0.1.0"}

@app.post("/api/v1/auth/register")
async def register(data: dict):
    """Mock registration."""
    email = data.get("email", "")
    return {
        "id": "user-123",
        "email": email,
        "full_name": data.get("full_name", ""),
        "is_active": True
    }

@app.post("/api/v1/auth/login-json")
async def login(data: dict):
    """Mock login."""
    return {
        "access_token": "test-token-" + str(hash(data.get("email", ""))),
        "token_type": "bearer",
        "user": {
            "id": "user-123",
            "email": data.get("email", "")
        }
    }

@app.get("/api/v1/auth/me")
async def me():
    """Mock current user."""
    return {"id": "user-123", "email": "test@byos.io"}

@app.get("/api/v1/dashboard/stats")
async def dashboard_stats():
    return {"total_cost": 123.45, "period": "month"}

@app.get("/api/v1/dashboard/system-status")
async def dashboard_system_status():
    return {"status": "operational", "uptime": 99.9}

@app.get("/api/v1/dashboard/recent-activity")
async def dashboard_recent_activity():
    return {"activities": []}

@app.get("/api/v1/dashboard/cost-trend")
async def dashboard_cost_trend():
    return {"trend": "stable"}

@app.get("/api/v1/dashboard/provider-breakdown")
async def dashboard_provider_breakdown():
    return {"providers": {}}

@app.get("/api/v1/dashboard/savings-summary")
async def dashboard_savings_summary():
    return {"savings": 45.67}

@app.get("/api/v1/dashboard/anomalies-summary")
async def dashboard_anomalies_summary():
    return {"anomalies": 0}

@app.get("/api/v1/dashboard/budget-status")
async def dashboard_budget_status():
    return {"status": "on_track"}

@app.get("/api/v1/budget")
async def get_budget():
    return {"budget": 1000.0}

@app.post("/api/v1/budget")
async def create_budget(data: dict):
    return {"id": "budget-123", "amount": data.get("amount", 100.0)}

@app.get("/api/v1/anomalies")
async def get_anomalies():
    return {"anomalies": []}

@app.post("/api/v1/anomalies/detect")
async def detect_anomalies(data: dict):
    return {"anomalies": [], "detected_at": "2026-02-24T12:00:00Z"}

@app.get("/api/v1/routing/policy")
async def get_routing_policy():
    return {"policies": []}

@app.get("/api/v1/audit/logs")
async def get_audit_logs():
    return {"logs": []}

@app.get("/api/v1/insights/savings")
async def get_savings_insights():
    return {"insights": []}

@app.get("/api/v1/cost/summary")
async def get_cost_summary():
    return {"summary": {}}

@app.post("/api/v1/cost/predict")
async def predict_cost(data: dict):
    return {"estimated_cost": 1.23}

@app.get("/api/v1/plugins")
async def get_plugins():
    return {"plugins": []}

@app.get("/api/v1/workspaces/current")
async def get_current_workspace():
    return {"id": "ws-123", "name": "Default"}

# ClipCrafter
@app.get("/api/v1/clipcrafter/clips")
async def clipcrafter_clips():
    return {"clips": []}

@app.get("/api/v1/clipcrafter/projects")
async def clipcrafter_projects():
    return {"projects": []}

@app.get("/api/v1/clipcrafter/templates")
async def clipcrafter_templates():
    return {"templates": []}

# TrapMaster
@app.get("/api/v1/trapmaster/projects")
async def trapmaster_projects():
    return {"projects": []}

@app.get("/api/v1/trapmaster/tracks")
async def trapmaster_tracks():
    return {"tracks": []}

@app.get("/api/v1/trapmaster/samples")
async def trapmaster_samples():
    return {"samples": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
