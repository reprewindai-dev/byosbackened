#!/usr/bin/env python
"""
BYOS Backend - Single File Approach
All-in-one local Windows + Ollama setup
No Docker, no dependencies, just pure Python
"""
import os
import sys
import json
import uuid
import time
import sqlite3
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
import http.client
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
CONFIG = {
    "HOST": "0.0.0.0",
    "PORT": 8003,
    "OLLAMA_URL": "http://127.0.0.1:11434",
    "OLLAMA_MODEL": "llama3.2:1b",
    "DB_PATH": "byos_local.db",
    "API_KEYS": {
        "agencyos_key_123": {"tenant_id": "agencyos", "name": "AgencyOS", "limit": 1000},
        "battlearena_key_456": {"tenant_id": "battlearena", "name": "BattleArena", "limit": 2000},
        "luminode_key_789": {"tenant_id": "luminode", "name": "LumiNode", "limit": 500}
    }
}

# Data Models
@dataclass
class Execution:
    execution_id: str
    tenant_id: str
    prompt: str
    response: str
    model: str
    tokens_generated: int
    execution_time_ms: int
    timestamp: str

@dataclass
class Tenant:
    tenant_id: str
    name: str
    api_key: str
    daily_limit: int
    daily_used: int
    last_reset: str
    is_active: bool

@dataclass
class StatusResponse:
    uptime_seconds: int
    db_ok: bool
    ollama_ok: bool
    active_tenants: int
    total_executions: int

class BYOSBackend:
    """Single-file BYOS backend with SQLite and direct HTTP"""
    
    def __init__(self):
        self.start_time = time.time()
        self.db_path = CONFIG["DB_PATH"]
        self.init_database()
        logger.info("BYOS Backend initialized")
        logger.info(f"Ollama URL: {CONFIG['OLLAMA_URL']}")
        logger.info(f"Model: {CONFIG['OLLAMA_MODEL']}")
        logger.info(f"Database: {self.db_path}")
    
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                tenant_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                api_key TEXT UNIQUE NOT NULL,
                daily_limit INTEGER DEFAULT 1000,
                daily_used INTEGER DEFAULT 0,
                last_reset TEXT DEFAULT CURRENT_DATE,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS executions (
                execution_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,
                model TEXT NOT NULL,
                tokens_generated INTEGER DEFAULT 0,
                execution_time_ms INTEGER DEFAULT 0,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id)
            )
        """)
        
        # Insert default tenants
        for api_key, tenant_info in CONFIG["API_KEYS"].items():
            cursor.execute("""
                INSERT OR IGNORE INTO tenants (tenant_id, name, api_key, daily_limit)
                VALUES (?, ?, ?, ?)
            """, (tenant_info["tenant_id"], tenant_info["name"], api_key, tenant_info["limit"]))
        
        conn.commit()
        conn.close()
        logger.info("Database initialized")
    
    def check_ollama_status(self) -> bool:
        """Check if Ollama is running"""
        try:
            conn = http.client.HTTPConnection("127.0.0.1", 11434, timeout=5)
            conn.request("GET", "/api/tags")
            response = conn.getresponse()
            conn.close()
            return response.status == 200
        except Exception as e:
            logger.error(f"Ollama check failed: {e}")
            return False
    
    def call_ollama(self, prompt: str, model: str = None) -> str:
        """Call Ollama API directly"""
        if model is None:
            model = CONFIG["OLLAMA_MODEL"]
        
        try:
            conn = http.client.HTTPConnection("127.0.0.1", 11434, timeout=60)
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }
            
            headers = {"Content-Type": "application/json"}
            conn.request("POST", "/api/generate", json.dumps(payload).encode(), headers)
            
            response = conn.getresponse()
            data = json.loads(response.read().decode())
            conn.close()
            
            if response.status == 200:
                return data.get("response", "")
            else:
                raise Exception(f"Ollama error: {data}")
                
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            raise
    
    def verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Verify API key and return tenant info"""
        tenant_info = CONFIG["API_KEYS"].get(api_key)
        if not tenant_info:
            return None
        
        # Check daily limit
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Reset daily count if needed
        cursor.execute("""
            UPDATE tenants 
            SET daily_used = 0, last_reset = CURRENT_DATE 
            WHERE tenant_id = ? AND last_reset < CURRENT_DATE
        """, (tenant_info["tenant_id"],))
        
        # Get current usage
        cursor.execute("""
            SELECT daily_used, is_active FROM tenants 
            WHERE tenant_id = ?
        """, (tenant_info["tenant_id"],))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[1]:  # is_active
            return None
        
        daily_used = result[0]
        if daily_used >= tenant_info["limit"]:
            raise Exception(f"Daily limit exceeded: {daily_used}/{tenant_info['limit']}")
        
        return tenant_info
    
    def record_execution(self, execution: Execution):
        """Record execution in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insert execution
        cursor.execute("""
            INSERT INTO executions 
            (execution_id, tenant_id, prompt, response, model, tokens_generated, execution_time_ms, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            execution.execution_id,
            execution.tenant_id,
            execution.prompt,
            execution.response,
            execution.model,
            execution.tokens_generated,
            execution.execution_time_ms,
            execution.timestamp
        ))
        
        # Update daily usage
        cursor.execute("""
            UPDATE tenants 
            SET daily_used = daily_used + 1 
            WHERE tenant_id = ?
        """, (execution.tenant_id,))
        
        conn.commit()
        conn.close()
    
    def execute_llm(self, api_key: str, prompt: str, model: str = None) -> Dict[str, Any]:
        """Execute LLM inference"""
        # Verify API key
        tenant_info = self.verify_api_key(api_key)
        if not tenant_info:
            raise Exception("Invalid or inactive API key")
        
        # Generate execution ID
        execution_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Call Ollama
            response_text = self.call_ollama(prompt, model)
            
            # Calculate metrics
            end_time = time.time()
            execution_time_ms = int((end_time - start_time) * 1000)
            tokens_generated = len(response_text.split())
            
            # Create execution record
            execution = Execution(
                execution_id=execution_id,
                tenant_id=tenant_info["tenant_id"],
                prompt=prompt,
                response=response_text,
                model=model or CONFIG["OLLAMA_MODEL"],
                tokens_generated=tokens_generated,
                execution_time_ms=execution_time_ms,
                timestamp=datetime.utcnow().isoformat()
            )
            
            # Record execution
            self.record_execution(execution)
            
            return {
                "response": response_text,
                "model": model or CONFIG["OLLAMA_MODEL"],
                "tenant_id": tenant_info["tenant_id"],
                "execution_id": execution_id,
                "timestamp": execution.timestamp,
                "tokens_generated": tokens_generated,
                "execution_time_ms": execution_time_ms
            }
            
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Get system status"""
        uptime = int(time.time() - self.start_time)
        ollama_ok = self.check_ollama_status()
        
        # Get database stats
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM tenants WHERE is_active = 1")
        active_tenants = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM executions")
        total_executions = cursor.fetchone()[0]
        
        conn.close()
        
        return StatusResponse(
            uptime_seconds=uptime,
            db_ok=True,
            ollama_ok=ollama_ok,
            active_tenants=active_tenants,
            total_executions=total_executions
        ).__dict__
    
    def get_tenant_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get tenant statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get tenant info
        cursor.execute("""
            SELECT name, daily_limit, daily_used, is_active 
            FROM tenants WHERE tenant_id = ?
        """, (tenant_id,))
        
        tenant = cursor.fetchone()
        if not tenant:
            conn.close()
            raise Exception("Tenant not found")
        
        # Get execution stats
        cursor.execute("""
            SELECT COUNT(*), AVG(execution_time_ms), SUM(tokens_generated)
            FROM executions WHERE tenant_id = ?
        """, (tenant_id,))
        
        exec_stats = cursor.fetchone()
        
        conn.close()
        
        return {
            "tenant_id": tenant_id,
            "name": tenant[0],
            "daily_limit": tenant[1],
            "daily_used": tenant[2],
            "is_active": tenant[3],
            "total_executions": exec_stats[0] or 0,
            "avg_execution_time_ms": round(exec_stats[1] or 0, 2),
            "total_tokens_generated": exec_stats[2] or 0
        }

# Simple HTTP Server
import http.server
import socketserver
from urllib.parse import urlparse, parse_qs

class BYOSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler for BYOS Backend"""
    
    def __init__(self, *args, **kwargs):
        self.backend = BYOSBackend()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed = urlparse(self.path)
        
        if parsed.path == "/":
            self.send_json_response({
                "service": "BYOS Backend - Single File",
                "version": "1.0.0",
                "endpoints": {
                    "exec": "POST /v1/exec",
                    "status": "GET /status",
                    "health": "GET /health"
                },
                "ollama_config": {
                    "url": CONFIG["OLLAMA_URL"],
                    "model": CONFIG["OLLAMA_MODEL"]
                }
            })
        
        elif parsed.path == "/health":
            self.send_json_response({
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        elif parsed.path == "/status":
            status = self.backend.get_status()
            self.send_json_response(status)
        
        elif parsed.path.startswith("/tenant/"):
            tenant_id = parsed.path.split("/")[-1]
            try:
                stats = self.backend.get_tenant_stats(tenant_id)
                self.send_json_response(stats)
            except Exception as e:
                self.send_error_response(404, str(e))
        
        else:
            self.send_error_response(404, "Endpoint not found")
    
    def do_POST(self):
        """Handle POST requests"""
        parsed = urlparse(self.path)
        
        if parsed.path == "/v1/exec":
            self.handle_exec_request()
        else:
            self.send_error_response(404, "Endpoint not found")
    
    def handle_exec_request(self):
        """Handle execution request"""
        try:
            # Get API key from headers
            api_key = self.headers.get("X-API-Key")
            if not api_key:
                self.send_error_response(401, "Missing X-API-Key header")
                return
            
            # Read request body
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                body = self.rfile.read(content_length).decode('utf-8')
                data = json.loads(body) if body else {}
            else:
                data = {}
            
            prompt = data.get("prompt")
            if not prompt:
                self.send_error_response(400, "Missing prompt field")
                return
            
            model = data.get("model", CONFIG["OLLAMA_MODEL"])
            
            # Execute LLM
            result = self.backend.execute_llm(api_key, prompt, model)
            self.send_json_response(result)
            
        except json.JSONDecodeError:
            self.send_error_response(400, "Invalid JSON")
        except Exception as e:
            self.send_error_response(500, str(e))
    
    def send_json_response(self, data, status_code=200):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-Key")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
    
    def send_error_response(self, status_code, message):
        """Send error response"""
        self.send_json_response({"error": message}, status_code)
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-Key")
        self.end_headers()
    
    def log_message(self, format, *args):
        """Custom logging"""
        logger.info(f"{self.address_string()} - {format % args}")

def start_server():
    """Start the BYOS backend server"""
    logger.info("Starting BYOS Backend - Single File Approach")
    logger.info(f"Server: http://{CONFIG['HOST']}:{CONFIG['PORT']}")
    logger.info(f"API Docs: http://{CONFIG['HOST']}:{CONFIG['PORT']}/")
    logger.info(f"Health: http://{CONFIG['HOST']}:{CONFIG['PORT']}/health")
    logger.info(f"Status: http://{CONFIG['HOST']}:{CONFIG['PORT']}/status")
    
    # Create server
    with socketserver.TCPServer((CONFIG["HOST"], CONFIG["PORT"]), BYOSHTTPRequestHandler) as httpd:
        logger.info(f"Server started on port {CONFIG['PORT']}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        finally:
            httpd.server_close()

if __name__ == "__main__":
    # Check Ollama status first
    backend = BYOSBackend()
    if not backend.check_ollama_status():
        logger.error("❌ Ollama is not running!")
        logger.error(f"Please start Ollama: {CONFIG['OLLAMA_URL']}")
        logger.error("Install model: ollama pull llama3.2:1b")
        sys.exit(1)
    
    logger.info("✅ Ollama is running")
    logger.info("🚀 Starting BYOS Backend...")
    start_server()
