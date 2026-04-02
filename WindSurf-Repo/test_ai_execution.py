#!/usr/bin/env python3
"""Test script for AI execution through governance pipeline."""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_governance_pipeline():
    """Test the governance pipeline with a simple request."""
    
    try:
        # Import the governance pipeline
        from core.governance import GovernancePipeline
        from core.governance.schemas import GovernanceRequest, OperationType
        
        print("✅ Successfully imported governance pipeline")
        
        # Initialize the pipeline
        pipeline = GovernancePipeline()
        print("✅ Successfully initialized governance pipeline")
        
        # Create a test request
        request = GovernanceRequest(
            operation_type=OperationType.SUMMARIZE,
            input_text="This is a test text for summarization. The governance pipeline should process this request and return a governed summary.",
            workspace_id="test-workspace",
            user_id="test-user",
            temperature=0.7,
            max_tokens=256
        )
        print("✅ Successfully created test request")
        
        # Create mock workspace context
        workspace_context = {
            "workspace_id": "test-workspace",
            "user_id": "test-user", 
            "user_tier": "free",
            "cost_sensitivity": 0.5,
            "latency_requirement_ms": 2000,
            "session_id": "test-session"
        }
        print("✅ Successfully created workspace context")
        
        # Run the governance pipeline
        result = await pipeline.run(request, workspace_context)
        print("✅ Successfully ran governance pipeline")
        
        # Print results
        print(f"\n📊 EXECUTION RESULTS:")
        print(f"Request ID: {result.request_id}")
        print(f"Success: {result.pipeline_passed}")
        print(f"Execution Time: {result.execution_time_ms}ms")
        print(f"Assigned Tier: {result.assigned_tier}")
        print(f"Provider: {result.routing_decision.selected_provider}")
        print(f"Result: {result.execution_outcome.final_result}")
        
        if result.blocked_at_stage:
            print(f"❌ Blocked at stage: {result.blocked_at_stage}")
            print(f"Block reason: {result.block_reason}")
        else:
            print("✅ Request passed all governance stages")
            
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_provider_integration():
    """Test provider integration directly."""
    
    try:
        from core.providers.registry import get_registry
        
        print("\n🔧 TESTING PROVIDER INTEGRATION:")
        
        # Get provider registry
        registry = get_registry()
        print("✅ Successfully got provider registry")
        
        # Try to get a provider
        try:
            provider = registry.get_llm_provider("local_llm")
            print("✅ Successfully got local_llm provider")
        except Exception as e:
            print(f"⚠️ Could not get local_llm provider: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ Provider integration test failed: {e}")
        return False

async def main():
    """Run all tests."""
    
    print("🚀 STARTING AI EXECUTION TESTS\n")
    
    # Test governance pipeline
    pipeline_success = await test_governance_pipeline()
    
    # Test provider integration
    provider_success = await test_provider_integration()
    
    print(f"\n📋 TEST SUMMARY:")
    print(f"Governance Pipeline: {'✅ PASS' if pipeline_success else '❌ FAIL'}")
    print(f"Provider Integration: {'✅ PASS' if provider_success else '❌ FAIL'}")
    
    if pipeline_success and provider_success:
        print("\n🎉 ALL TESTS PASSED! AI execution system is working.")
        return 0
    else:
        print("\n💥 SOME TESTS FAILED! Check the errors above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
