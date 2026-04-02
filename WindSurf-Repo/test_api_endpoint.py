#!/usr/bin/env python3
"""Test the AI execution API endpoint."""

import asyncio
import aiohttp
import json
import sys

async def test_ai_execution_endpoint():
    """Test the /api/v1/governance/execute endpoint."""
    
    # Test data
    test_request = {
        "operation_type": "summarize",
        "input_text": "This is a test text for the AI execution endpoint. The sovereign governance pipeline should process this request and return a governed summary that meets all quality and compliance requirements.",
        "temperature": 0.7,
        "max_tokens": 256,
        "demo_context": {
            "session_id": "test-session-123",
            "demo_token": "test-token",
            "lead_id": "test-lead"
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test the health endpoint first
            print("🔍 Testing health endpoint...")
            async with session.get("http://localhost:8000/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    print(f"✅ Health check passed: {health_data}")
                else:
                    print(f"❌ Health check failed: {response.status}")
                    return False
            
            # Test the governance execute endpoint
            print("\n🚀 Testing AI execution endpoint...")
            headers = {"Content-Type": "application/json"}
            
            async with session.post(
                "http://localhost:8000/api/v1/governance/execute",
                json=test_request,
                headers=headers
            ) as response:
                
                print(f"Status code: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print("✅ AI execution successful!")
                    print(f"Request ID: {result.get('request_id')}")
                    print(f"Success: {result.get('success')}")
                    print(f"Execution Time: {result.get('execution_time_ms')}ms")
                    print(f"Coherence Score: {result.get('coherence_score')}")
                    print(f"Risk Level: {result.get('risk_level')}")
                    print(f"Patterns Applied: {result.get('patterns_applied')}")
                    print(f"Result: {result.get('result', 'No result returned')}")
                    return True
                    
                else:
                    error_text = await response.text()
                    print(f"❌ AI execution failed: {response.status}")
                    print(f"Error: {error_text}")
                    return False
                    
    except aiohttp.ClientError as e:
        print(f"❌ Connection error: {e}")
        print("💡 Make sure the API server is running on localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

async def main():
    """Run the API test."""
    
    print("🧪 TESTING AI EXECUTION API ENDPOINT")
    print("=" * 50)
    
    success = await test_ai_execution_endpoint()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 API TEST PASSED! The AI execution endpoint is working.")
        return 0
    else:
        print("💥 API TEST FAILED! Check the errors above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
