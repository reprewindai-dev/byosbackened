#!/usr/bin/env python
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add Scripts to PATH
scripts_path = r"C:\Python311\Scripts"
os.environ["PATH"] = scripts_path + os.pathsep + os.environ.get("PATH", "")

# Add site-packages to Python path
site_packages = r"C:\Python311\Lib\site-packages"
sys.path.insert(0, site_packages)

# Create minimal FastAPI server
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Dependencies should be installed. Trying to install...")
    
    # Try to install missing packages
    import subprocess
    pip_exe = os.path.join(scripts_path, "pip.exe")
    packages = ["fastapi", "uvicorn", "pydantic"]
    
    for package in packages:
        try:
            print(f"Installing {package}...")
            env = os.environ.copy()
            env["PATH"] = scripts_path + os.pathsep + env.get("PATH", "")
            subprocess.check_call([pip_exe, "install", package], env=env)
            print(f"Installed {package}")
        except Exception as install_error:
            print(f"Failed to install {package}: {install_error}")
    
    # Try importing again
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import HTMLResponse, JSONResponse
        from fastapi.middleware.cors import CORSMiddleware
        from pydantic import BaseModel
        import uvicorn
        print("Successfully imported all dependencies")
    except ImportError as e:
        print(f"Still missing dependencies: {e}")
        sys.exit(1)

app = FastAPI(title="BYOS AI Backend - Minimal", version="0.1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data models
class ExecutiveSummary(BaseModel):
    net_profit: float
    gross_margin_percent: float
    run_rate: float
    burn_rate: float

class RevenueMetrics(BaseModel):
    total_revenue: float
    growth_rate: float
    mrr: float
    by_tier: dict

class CostMetrics(BaseModel):
    total_cost: float
    daily_burn: float
    power_cost: float

class PowerMetrics(BaseModel):
    total_energy_kwh: float
    co2_emissions_kg: float
    efficiency_percent: float

class Alert(BaseModel):
    severity: str
    title: str
    message: str
    impact: str

class ExecutiveOverview(BaseModel):
    period_days: int
    last_updated: str
    executive_summary: ExecutiveSummary
    revenue: RevenueMetrics
    costs: CostMetrics
    power: PowerMetrics
    alerts: list[Alert]

# Mock authentication
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: dict

@app.post("/api/v1/auth/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """Simple mock authentication"""
    if credentials.username == "admin" and credentials.password == "admin123":
        return LoginResponse(
            access_token="mock_token_12345",
            token_type="bearer",
            expires_in=1800,
            user={
                "id": "admin",
                "username": "admin",
                "email": "admin@byos-ai.com",
                "role": "admin"
            }
        )
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/api/v1/executive/dashboard/overview", response_model=ExecutiveOverview)
async def get_executive_overview(days: int = 30):
    """Mock executive dashboard data"""
    return ExecutiveOverview(
        period_days=days,
        last_updated=datetime.utcnow().isoformat(),
        executive_summary=ExecutiveSummary(
            net_profit=125000.00,
            gross_margin_percent=68.5,
            run_rate=450000.00,
            burn_rate=85000.00
        ),
        revenue=RevenueMetrics(
            total_revenue=275000.00,
            growth_rate=12.5,
            mrr=450000.00,
            by_tier={
                "STARTER": {"revenue": 50000.0, "customers": 120, "arpu": 416.67},
                "PRO": {"revenue": 150000.0, "customers": 80, "arpu": 1875.00},
                "ENTERPRISE": {"revenue": 75000.0, "customers": 15, "arpu": 5000.00}
            }
        ),
        costs=CostMetrics(
            total_cost=150000.00,
            daily_burn=5000.00,
            power_cost=25000.00
        ),
        power=PowerMetrics(
            total_energy_kwh=1250.5,
            co2_emissions_kg=875.3,
            efficiency_percent=92.4
        ),
        alerts=[
            Alert(
                severity="info",
                title="Power optimization opportunity",
                message="Enable carbon-aware routing for heavy workloads",
                impact="Potential energy savings > 12%"
            ),
            Alert(
                severity="warning",
                title="Churn spike detected",
                message="Churn rate 6.2% exceeds target",
                impact="Trigger win-back campaigns"
            )
        ]
    )

@app.post("/api/v1/executive/dashboard/pricing/adjust")
async def adjust_pricing():
    """Mock pricing adjustment endpoint"""
    return {"status": "success", "message": "Pricing adjustment queued"}

@app.get("/api/v1/executive/dashboard/controls/guardrails")
async def get_guardrails():
    """Mock guardrails configuration"""
    return {
        "daily_budget": 2500.0,
        "monthly_budget": 60000.0,
        "power_saving_mode": False,
        "provider_spend_caps": {"openai": 20000, "huggingface": 5000, "local": 1500},
        "pricing_floor_margin": 30.0,
        "cost_strategy": "balanced",
        "updated_by": "system"
    }

@app.post("/api/v1/executive/dashboard/controls/guardrails")
async def set_guardrails():
    """Mock guardrails update endpoint"""
    return {"status": "success", "message": "Guardrails updated"}

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the executive dashboard"""
    dashboard_path = Path("executive_admin_dashboard.html")
    if dashboard_path.exists():
        return dashboard_path.read_text()
    return "<h1>BYOS AI Backend</h1><p>Executive dashboard not found</p>"

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    print("Starting minimal BYOS AI Backend server...")
    print("Executive dashboard will be available at: http://localhost:8000")
    print("API docs at: http://localhost:8000/docs")
    print("Health check at: http://localhost:8000/health")
    uvicorn.run(app, host="0.0.0.0", port=8000)
