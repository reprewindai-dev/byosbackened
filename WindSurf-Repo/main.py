#!/usr/bin/env python
"""
BYOS Backend - Local Windows + Ollama Setup
Multi-tenant API service with local LLM inference
"""
import os
import sys
import uuid
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import time
import psutil

from fastapi import FastAPI, HTTPException, Depends, status, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
import asyncpg
import aioredis
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://byos_user:byos_password@localhost:5432/byos_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://host.docker.internal:11434")
LLM_MODEL_DEFAULT = os.getenv("LLM_MODEL_DEFAULT", "llama3.2:1b")
LLM_FALLBACK = os.getenv("LLM_FALLBACK", "off")
JWT_SECRET = os.getenv("JWT_SECRET", "your_jwt_secret_here")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")

# Initialize FastAPI app
app = FastAPI(
    title="BYOS Backend - Local Ollama",
    description="Multi-tenant API with local LLM inference",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data Models
class ExecutionRequest(BaseModel):
    prompt: str = Field(..., description="Prompt for LLM execution")
    tenant_id: Optional[str] = Field(None, description="Tenant ID (resolved from API key)")
    model: Optional[str] = Field(LLM_MODEL_DEFAULT, description="LLM model to use")
    stream: Optional[bool] = Field(False, description="Whether to stream response")
    max_tokens: Optional[int] = Field(1000, description="Maximum tokens to generate")

class ExecutionResponse(BaseModel):
    response: str = Field(..., description="LLM response")
    model: str = Field(..., description="Model used")
    tenant_id: str = Field(..., description="Tenant ID")
    execution_id: str = Field(..., description="Execution ID")
    timestamp: str = Field(..., description="Execution timestamp")
    tokens_generated: int = Field(..., description="Number of tokens generated")
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")

class StatusResponse(BaseModel):
    uptime_seconds: int = Field(..., description="Server uptime in seconds")
    db_ok: bool = Field(..., description="Database connection status")
    redis_ok: bool = Field(..., description="Redis connection status")
    llm_ok: bool = Field(..., description="LLM service status")
    active_tenants: int = Field(..., description="Number of active tenants")
    total_executions: int = Field(..., description="Total executions served")

class Tenant(BaseModel):
    tenant_id: str = Field(..., description="Tenant UUID")
    name: str = Field(..., description="Tenant name")
    api_key: str = Field(..., description="API key for tenant")
    created_at: str = Field(..., description="Creation timestamp")
    is_active: bool = Field(..., description="Tenant active status")
    execution_limit: int = Field(..., description="Daily execution limit")

# Database and Redis connections
db_pool: Optional[asyncpg.Pool] = None
redis_client: Optional[aioredis.Redis] = None
start_time = time.time()

# API Key to Tenant mapping (in production, store in database)
API_KEYS = {
    "agencyos_key_123": {
        "tenant_id": "550e8400-e29b-41d4-a716-446655440001",
        "name": "AgencyOS",
        "is_active": True,
        "execution_limit": 1000
    },
    "battlearena_key_456": {
        "tenant_id": "550e8400-e29b-41d4-a716-446655440002", 
        "name": "BattleArena",
        "is_active": True,
        "execution_limit": 2000
    },
    "luminode_key_789": {
        "tenant_id": "550e8400-e29b-41d4-a716-446655440003",
        "name": "LumiNode", 
        "is_active": True,
        "execution_limit": 500
    }
}

async def init_database():
    """Initialize database connection and setup RLS"""
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20)
        logger.info("Database connection established")
        
        # Initialize RLS policies
        async with db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS tenants (
                    tenant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) NOT NULL,
                    api_key VARCHAR(255) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    is_active BOOLEAN DEFAULT true,
                    execution_limit INTEGER DEFAULT 1000
                );
                
                CREATE TABLE IF NOT EXISTS executions (
                    execution_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
                    prompt TEXT NOT NULL,
                    response TEXT NOT NULL,
                    model VARCHAR(100) NOT NULL,
                    tokens_generated INTEGER DEFAULT 0,
                    execution_time_ms INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                
                -- Enable RLS
                ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
                ALTER TABLE executions ENABLE ROW LEVEL SECURITY;
                
                -- RLS Policies
                CREATE POLICY tenant_isolation ON tenants
                    USING (tenant_id = current_setting('request.tenant_id', true)::UUID);
                    
                CREATE POLICY execution_isolation ON executions
                    USING (tenant_id = current_setting('request.tenant_id', true)::UUID);
            """)
            
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

async def init_redis():
    """Initialize Redis connection"""
    global redis_client
    try:
        redis_client = await aioredis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("Redis connection established")
        return True
    except Exception as e:
        logger.error(f"Redis initialization failed: {e}")
        return False

async def check_llm_status():
    """Check Ollama service status"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{LLM_BASE_URL}/api/tags")
            return response.status_code == 200
    except Exception as e:
        logger.error(f"LLM status check failed: {e}")
        return False

async def get_tenant_from_api_key(api_key: str = Header(..., alias="X-API-Key")):
    """Resolve tenant from API key"""
    tenant_info = API_KEYS.get(api_key)
    if not tenant_info or not tenant_info["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key"
        )
    return tenant_info

async def check_execution_limit(tenant_id: str, redis_key: str):
    """Check if tenant has exceeded execution limit"""
    try:
        current_count = await redis_client.get(redis_key)
        if current_count and int(current_count) >= API_KEYS[tenant_id]["execution_limit"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Daily execution limit exceeded"
            )
    except Exception as e:
        logger.error(f"Execution limit check failed: {e}")

async def call_ollama(prompt: str, model: str = LLM_MODEL_DEFAULT):
    """Call local Ollama API"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{LLM_BASE_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"LLM service error: {response.text}"
                )
            
            result = response.json()
            return result.get("response", "")
            
    except Exception as e:
        logger.error(f"Ollama call failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service unavailable"
        )

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting BYOS Backend - Local Ollama Setup")
    
    # Initialize database
    db_ok = await init_database()
    
    # Initialize Redis
    redis_ok = await init_redis()
    
    # Check LLM service
    llm_ok = await check_llm_status()
    
    logger.info(f"Services status - DB: {db_ok}, Redis: {redis_ok}, LLM: {llm_ok}")
    
    if not db_ok or not redis_ok:
        logger.error("Critical services failed to start")
        sys.exit(1)

@app.post("/v1/exec", response_model=ExecutionResponse)
async def execute_llm(
    request: ExecutionRequest,
    tenant_info: Dict[str, Any] = Depends(get_tenant_from_api_key)
):
    """Execute LLM inference with tenant isolation"""
    tenant_id = tenant_info["tenant_id"]
    execution_id = str(uuid.uuid4())
    start_time_ms = int(time.time() * 1000)
    
    try:
        # Check execution limit
        redis_key = f"tenant:{tenant_id}:daily_executions"
        await check_execution_limit(tenant_id, redis_key)
        
        # Set tenant context in database
        async with db_pool.acquire() as conn:
            await conn.execute(f"SET LOCAL request.tenant_id = '{tenant_id}'")
        
        # Call Ollama
        response_text = await call_ollama(request.prompt, request.model)
        
        # Calculate metrics
        end_time_ms = int(time.time() * 1000)
        execution_time_ms = end_time_ms - start_time_ms
        tokens_generated = len(response_text.split())
        
        # Log execution in database
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO executions (execution_id, tenant_id, prompt, response, model, tokens_generated, execution_time_ms)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                execution_id, tenant_id, request.prompt, response_text, request.model, tokens_generated, execution_time_ms
            )
        
        # Increment Redis counter
        await redis_client.incr(redis_key)
        await redis_client.expire(redis_key, 86400)  # 24 hours
        
        return ExecutionResponse(
            response=response_text,
            model=request.model,
            tenant_id=tenant_id,
            execution_id=execution_id,
            timestamp=datetime.utcnow().isoformat(),
            tokens_generated=tokens_generated,
            execution_time_ms=execution_time_ms
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Execution failed"
        )

@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get system status"""
    uptime_seconds = int(time.time() - start_time)
    
    # Check services
    db_ok = db_pool is not None
    redis_ok = redis_client is not None
    llm_ok = await check_llm_status()
    
    # Get metrics
    active_tenants = len([t for t in API_KEYS.values() if t["is_active"]])
    total_executions = 0
    
    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                result = await conn.fetchval("SELECT COUNT(*) FROM executions")
                total_executions = result
        except:
            pass
    
    return StatusResponse(
        uptime_seconds=uptime_seconds,
        db_ok=db_ok,
        redis_ok=redis_ok,
        llm_ok=llm_ok,
        active_tenants=active_tenants,
        total_executions=total_executions
    )

@app.get("/health")
async def health_check():
    """Simple health check"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "BYOS Backend - Local Ollama",
        "version": "1.0.0",
        "endpoints": {
            "exec": "/v1/exec",
            "status": "/status",
            "health": "/health",
            "docs": "/docs"
        },
        "llm_config": {
            "base_url": LLM_BASE_URL,
            "model": LLM_MODEL_DEFAULT,
            "fallback": LLM_FALLBACK
        }
    }

if __name__ == "__main__":
    logger.info("Starting BYOS Backend with local Ollama integration")
    logger.info(f"LLM Base URL: {LLM_BASE_URL}")
    logger.info(f"Default Model: {LLM_MODEL_DEFAULT}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=LOG_LEVEL.lower()
    )
