#!/usr/bin/env python3
"""Final production readiness verification."""
import sys
import traceback

def check_imports():
    """Verify all critical imports work."""
    print("🔍 Checking imports...")
    try:
        from apps.api.main import app
        print(f"  ✅ Main app loads: {len(app.routes)} routes")
    except Exception as e:
        print(f"  ❌ Main app failed: {e}")
        traceback.print_exc()
        return False
    
    # Test all routers
    routers = [
        "apps.api.routers.auth",
        "apps.api.routers.subscriptions", 
        "apps.api.routers.support_bot",
        "apps.api.routers.token_wallet",
        "apps.api.routers.audit",
        "apps.api.routers.billing",
        "apps.api.routers.budget",
        "apps.api.routers.compliance",
        "apps.api.routers.cost",
        "apps.api.routers.insights",
        "apps.api.routers.kill_switch",
        "apps.api.routers.routing",
        "apps.api.routers.privacy",
        "apps.api.routers.plugins",
    ]
    for router in routers:
        try:
            __import__(router)
            print(f"  ✅ {router}")
        except Exception as e:
            print(f"  ❌ {router}: {e}")
            return False
    
    return True

def check_models():
    """Verify database models."""
    print("\n🗄️  Checking models...")
    try:
        from db import models as db_models
        required = [
            "User", "Workspace", "APIKey", "UserSession",
            "Subscription", "PlanTier", "SubscriptionStatus", 
            "TokenWallet", "TokenTransaction",
            "SecurityEvent", "Alert",
        ]
        for model in required:
            if hasattr(db_models, model):
                print(f"  ✅ {model}")
            else:
                print(f"  ❌ Missing {model}")
                return False
    except Exception as e:
        print(f"  ❌ Models failed: {e}")
        return False
    return True

def check_config():
    """Check configuration."""
    print("\n⚙️  Checking config...")
    try:
        from core.config import get_settings
        s = get_settings()
        
        # Critical settings
        critical = [
            ("secret_key", s.secret_key),
            ("database_url", s.database_url),
            ("api_prefix", s.api_prefix),
            ("stripe_secret_key", s.stripe_secret_key),
            ("stripe_webhook_secret", s.stripe_webhook_secret),
            ("github_client_id", s.github_client_id),
            ("github_client_secret", s.github_client_secret),
        ]
        
        for name, val in critical:
            configured = bool(val) and val not in ("", None)
            status = "✅" if configured else "⚠️"
            print(f"  {status} {name}: {'SET' if configured else 'NOT SET'}")
            
        # CORS origins should not be wildcard
        if "*" in s.cors_origins:
            print("  ⚠️  CORS contains wildcard origins")
        else:
            print("  ✅ CORS origins properly configured")
            
    except Exception as e:
        print(f"  ❌ Config failed: {e}")
        return False
    return True

def check_middleware():
    """Verify security middleware."""
    print("\n🛡️  Checking middleware...")
    try:
        from core.security.zero_trust import ZeroTrustMiddleware, _PUBLIC_PATHS
        print(f"  ✅ ZeroTrust middleware: {len(_PUBLIC_PATHS)} public paths")
        
        from apps.api.middleware.locker_security_integration import LockerSecurityMiddleware
        print("  ✅ LockerSecurity middleware")
        
        from apps.api.middleware.request_security import RequestSecurityMiddleware
        print("  ✅ RequestSecurity middleware")
        
    except Exception as e:
        print(f"  ❌ Middleware failed: {e}")
        return False
    return True

def check_dependencies():
    """Check external dependencies."""
    print("\n📦 Checking dependencies...")
    deps = [
        ("fastapi", "FastAPI"),
        ("sqlalchemy", "SQLAlchemy"),
        ("stripe", "Stripe"),
        ("httpx", "HTTPX"),
        ("pydantic", "Pydantic"),
        ("redis", "Redis"),
    ]
    for module, name in deps:
        try:
            __import__(module)
            print(f"  ✅ {name}")
        except ImportError:
            print(f"  ❌ {name} missing")
            return False
    return True

def main():
    print("=" * 60)
    print("FINAL PRODUCTION READINESS CHECK")
    print("=" * 60)
    
    checks = [
        ("Imports", check_imports),
        ("Models", check_models),
        ("Config", check_config),
        ("Middleware", check_middleware),
        ("Dependencies", check_dependencies),
    ]
    
    all_passed = True
    for name, check_func in checks:
        if not check_func():
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL CHECKS PASSED - READY FOR PRODUCTION")
    else:
        print("❌ SOME CHECKS FAILED - FIX BEFORE DEPLOY")
        sys.exit(1)

if __name__ == "__main__":
    main()
