"""Debug registration endpoint to find the exact error."""
import sys
import os
sys.path.append(os.getcwd())

from fastapi.testclient import TestClient
from apps.api.main import app

def debug_registration():
    client = TestClient(app)
    
    # Test registration with detailed error
    response = client.post("/api/v1/auth/register", json={
        "email": "test_debug@example.com",
        "password": "TestPass123",
        "workspace_name": "Debug Workspace"
    })
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    # If it's a 500, let's try to catch the actual error
    if response.status_code == 500:
        print("500 error detected - checking server logs...")
        # The error should be in the server console

if __name__ == "__main__":
    debug_registration()
