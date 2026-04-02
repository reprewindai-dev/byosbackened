#!/usr/bin/env python3
"""
Minimal server test to validate AI execution system imports.
Run this to verify the system is working before starting the full server.
"""

import sys
import os

def test_imports():
    """Test all critical imports."""
    
    print("🧪 TESTING AI EXECUTION SYSTEM IMPORTS")
    print("=" * 50)
    
    try:
        # Test core governance imports
        print("📦 Testing governance imports...")
        from core.governance import GovernancePipeline
        from core.governance.schemas import GovernanceRequest, OperationType
        print("✅ Governance imports successful")
        
        # Test provider imports
        print("🔌 Testing provider imports...")
        from core.providers.registry import get_registry
        print("✅ Provider imports successful")
        
        # Test API router import
        print("🌐 Testing API router import...")
        from apps.api.routers.governance import router
        print("✅ API router import successful")
        
        # Test pipeline initialization
        print("🏗️  Testing pipeline initialization...")
        pipeline = GovernancePipeline()
        print("✅ Pipeline initialization successful")
        
        # Test creating a governance request
        print("📋 Testing request creation...")
        request = GovernanceRequest(
            operation_type=OperationType.SUMMARIZE,
            input_text="Test text for summarization",
            workspace_id="test-workspace",
            temperature=0.7,
            max_tokens=256
        )
        print("✅ Request creation successful")
        
        print("\n🎉 ALL IMPORTS SUCCESSFUL!")
        print("✅ The AI execution system is ready to run")
        print("\n📋 NEXT STEPS:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Start server: python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload")
        print("3. Test endpoint: python test_api_endpoint.py")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Run: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
