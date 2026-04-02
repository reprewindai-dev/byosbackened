#!/usr/bin/env python3
"""Local testing script for BYOS Command Center."""

import os
import sys
import uvicorn
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment variables for testing
os.environ["ENVIRONMENT"] = "local_test"
os.environ["API_PORT"] = "8765"

def run_backend():
    """Run the backend server on port 8765."""
    print("🚀 Starting BYOS Backend on http://localhost:8765")
    print("📊 Dashboard will be available at http://localhost:4321")
    print("⏹️  Press Ctrl+C to stop")
    
    uvicorn.run(
        "apps.api.main:app",
        host="localhost",
        port=8765,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    print("🎛️  BYOS Command Center - Local Testing Setup")
    print("=" * 50)
    run_backend()
