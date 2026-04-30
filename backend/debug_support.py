"""Debug support bot to find exact error."""
import asyncio
import sys
import os
sys.path.append(os.getcwd())

async def debug_support():
    from apps.api.routers.support_bot import SupportMessage
    from fastapi.testclient import TestClient
    from apps.api.main import app
    
    client = TestClient(app)
    
    # Test support bot with detailed error
    payload = SupportMessage(message="What plans do you offer?")
    response = client.post("/api/v1/support/chat", json=payload)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    # If it's a 500, let's try to catch the actual error
    if response.status_code == 500:
        print("500 error detected - checking server logs...")
        # The error should be in the server console

if __name__ == "__main__":
    asyncio.run(debug_support())
