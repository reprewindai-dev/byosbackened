#!/usr/bin/env python3
"""
Stripe Integration Test Script
Validates that Stripe is properly configured and working.
"""

import os
import sys

def test_stripe_integration():
    """Test Stripe configuration and basic functionality."""
    
    print("💳 STRIPE INTEGRATION TEST")
    print("=" * 40)
    
    try:
        # Test imports
        print("📦 Testing Stripe imports...")
        import stripe
        from core.config import get_settings
        from apps.api.routers.stripe_billing import router
        print("✅ Stripe imports successful")
        
        # Test configuration
        print("⚙️  Testing Stripe configuration...")
        settings = get_settings()
        
        if not settings.stripe_secret_key:
            print("❌ Stripe secret key not configured")
            return False
            
        if not settings.stripe_publishable_key:
            print("❌ Stripe publishable key not configured")
            return False
            
        print("✅ Stripe keys configured")
        print(f"   Secret key: {settings.stripe_secret_key[:20]}...")
        print(f"   Publishable key: {settings.stripe_publishable_key[:20]}...")
        
        # Test Stripe API connection
        print("🔌 Testing Stripe API connection...")
        stripe.api_key = settings.stripe_secret_key
        
        try:
            # Test account retrieval (this will validate the API key)
            account = stripe.Account.retrieve()
            print("✅ Stripe API connection successful")
            print(f"   Account ID: {account.id}")
            print(f"   Country: {account.country}")
            print(f"   Business type: {account.business_profile.get('business_type', 'N/A')}")
        except stripe.error.AuthenticationError as e:
            print(f"❌ Stripe authentication failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Stripe API error: {e}")
            return False
        
        # Test billing plans
        print("📋 Testing billing plans...")
        from apps.api.routers.stripe_billing import BYOS_PLANS
        
        if not BYOS_PLANS:
            print("❌ No billing plans configured")
            return False
            
        print(f"✅ Found {len(BYOS_PLANS)} billing plans:")
        for plan_id, plan in BYOS_PLANS.items():
            print(f"   - {plan['name']}: ${plan['price_monthly']/100:.2f}/month")
        
        print("\n🎉 STRIPE INTEGRATION TEST PASSED!")
        print("✅ Stripe is properly configured and ready for billing")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Install stripe: pip install stripe")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def show_billing_endpoints():
    """Show available billing endpoints."""
    
    print("\n💰 AVAILABLE BILLING ENDPOINTS:")
    print("=" * 40)
    
    endpoints = [
        "POST /api/v1/stripe/checkout - Create checkout session",
        "POST /api/v1/stripe/portal - Create customer portal session", 
        "GET  /api/v1/stripe/plans - List available plans",
        "GET  /api/v1/stripe/subscription - Get current subscription",
        "POST /api/v1/stripe/subscribe - Create subscription",
        "POST /api/v1/stripe/cancel - Cancel subscription",
        "GET  /api/v1/stripe/status - Poll subscription status (no webhooks)"
    ]
    
    for endpoint in endpoints:
        print(f"   {endpoint}")

def show_next_steps():
    """Show next steps for Stripe setup."""
    
    print("\n📋 NEXT STEPS (NO WEBHOOKS):")
    print("=" * 40)
    
    steps = [
        "1. ✅ Stripe keys configured (LIVE mode)",
        "2. ✅ Polling service monitors subscriptions every 15 minutes",
        "3. ✅ System works without webhook setup",
        "4. Test billing flow with checkout sessions",
        "5. Set up subscription management",
        "6. Configure billing notifications (optional)"
    ]
    
    for step in steps:
        print(f"   {step}")
    
    print("\n🔄 POLLING INFO:")
    print("   - Subscriptions checked every 15 minutes")
    print("   - Payment status updated automatically")
    print("   - No webhook endpoint required")
    print("   - Lower complexity, easier deployment")

if __name__ == "__main__":
    success = test_stripe_integration()
    
    if success:
        show_billing_endpoints()
        show_next_steps()
        sys.exit(0)
    else:
        print("\n❌ Stripe integration test failed")
        print("Please check your configuration and try again")
        sys.exit(1)
