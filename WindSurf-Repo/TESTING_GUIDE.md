# 🧪 COMPLETE APP TESTING GUIDE

## 🚀 QUICK START

### Option 1: One-Click Testing
```bash
# Double-click this file:
TEST_EVERYTHING.bat
```

### Option 2: Manual Testing
```bash
# 1. Validate dependencies
python validate_deps.py

# 2. Start server (if not running)
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# 3. Run comprehensive tests
python test_full_app.py
```

## 📋 WHAT GETS TESTED

### 🏥 Health Endpoints
- ✅ Root endpoint (`/`)
- ✅ Health check (`/health`)
- ✅ API health (`/api/v1/health`)

### 🤖 AI Execution System
- ✅ Sovereign governance pipeline (12 layers)
- ✅ AI provider integration
- ✅ Risk scoring and tier assignment
- ✅ Quality validation and coherence scoring
- ✅ All operation types (summarize, chat, embed)

### 💳 Stripe Billing
- ✅ Billing plans retrieval
- ✅ Checkout session creation
- ✅ Payment processing (polling mode)
- ✅ Subscription management

### 🌐 API Endpoints
- ✅ Apps management
- ✅ Workspaces
- ✅ Governance system
- ✅ Billing and cost tracking
- ✅ Audit logs
- ✅ Metrics and monitoring

### 🗄️ Database & Infrastructure
- ✅ Database connectivity
- ✅ Session management
- ✅ Cache system (Redis)

### 🔌 Provider System
- ✅ AI provider registry
- ✅ Local LLM integration
- ✅ HuggingFace integration
- ✅ Fallback mechanisms

## 🎯 EXPECTED RESULTS

### ✅ PASSING TESTS MEAN:
- AI execution system is fully functional
- Sovereign governance pipeline working
- Stripe billing ready for live transactions
- All API endpoints responding
- Database connectivity stable
- Provider system operational

### ⚠️ COMMON ISSUES & FIXES:

#### Server Not Running
```
❌ Server not running at http://localhost:8000
```
**Fix**: The test script will auto-start the server

#### Missing Dependencies
```
❌ Package missing: stripe
```
**Fix**: Run `pip install stripe` or use `validate_deps.py`

#### Stripe Configuration
```
❌ Stripe authentication failed
```
**Fix**: Check `.env` file has correct Stripe keys

#### Database Issues
```
❌ Database connectivity failed
```
**Fix**: Ensure SQLite file exists or PostgreSQL is running

## 🔧 MANUAL TESTING OPTIONS

### Test AI Execution
```bash
curl -X POST http://localhost:8000/api/v1/governance/execute \
     -H "Content-Type: application/json" \
     -d '{
       "operation_type": "summarize",
       "input_text": "Test text for AI execution",
       "temperature": 0.7,
       "max_tokens": 256
     }'
```

### Test Stripe Billing
```bash
# View plans
curl http://localhost:8000/api/v1/stripe/plans

# Create checkout
curl -X POST http://localhost:8000/api/v1/stripe/checkout \
     -H "Content-Type: application/json" \
     -d '{
       "plan_id": "starter",
       "success_url": "http://localhost:3000/success",
       "cancel_url": "http://localhost:3000/cancel"
     }'
```

### Test Health
```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/health
```

## 📊 TEST RESULTS INTERPRETATION

### Success Indicators:
- ✅ **All health endpoints pass** - System is running
- ✅ **AI execution succeeds** - Governance pipeline working
- ✅ **Stripe checkout creates** - Billing system ready
- ✅ **Database responds** - Data layer functional
- ✅ **90%+ pass rate** - Production ready

### Warning Indicators:
- ⚠️ **Some endpoints fail** - Check specific error messages
- ⚠️ **AI execution slow** - Check provider configuration
- ⚠️ **Stripe auth issues** - Verify API keys

### Failure Indicators:
- ❌ **Server won't start** - Check Python/dependencies
- ❌ **Database errors** - Check connection strings
- ❌ **All tests fail** - System needs troubleshooting

## 🚀 PRODUCTION READINESS

### ✅ READY FOR PRODUCTION WHEN:
- All tests pass (100% success rate)
- AI execution working with real providers
- Stripe billing processes live transactions
- Governance pipeline validates all requests
- Database operations stable
- Security headers and CORS configured

### ⚠️ BEFORE GOING LIVE:
1. Test with real Stripe transactions (small amounts)
2. Verify governance pipeline with real AI requests
3. Test all operation types (summarize, chat, embed)
4. Validate subscription lifecycle
5. Check error handling and edge cases

## 🆘 GETTING HELP

### Test Failures:
1. Check `validate_deps.py` for missing packages
2. Verify `.env` configuration
3. Check server logs for detailed errors
4. Ensure ports 8000 and 3000 are available

### Common Fixes:
- `pip install -r requirements.txt`
- Restart the server
- Check environment variables
- Verify Stripe keys are valid

---

**Ready to test? Run `TEST_EVERYTHING.bat` now!**
