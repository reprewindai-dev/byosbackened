# Production Deployment Checklist

## 🚀 Pre-Deployment

### Environment Variables (REQUIRED)
- [ ] `SECRET_KEY` - Generate with `openssl rand -hex 32`
- [ ] `ENCRYPTION_KEY` - Generate with `openssl rand -hex 32`
- [ ] `DATABASE_URL` - PostgreSQL connection string
- [ ] `REDIS_URL` - Redis connection string
- [ ] `STRIPE_SECRET_KEY` - From Stripe dashboard
- [ ] `STRIPE_WEBHOOK_SECRET` - From Stripe webhook settings
- [ ] `GITHUB_CLIENT_ID` - GitHub OAuth app
- [ ] `GITHUB_CLIENT_SECRET` - GitHub OAuth app
- [ ] `CORS_ORIGINS` - Your frontend domains (no wildcard)

### Database Setup
- [ ] PostgreSQL database created
- [ ] Run migrations: `alembic upgrade head`
- [ ] Verify tables exist: `token_wallets`, `token_transactions`, `subscriptions`
- [ ] Set up database backups

### Redis Setup
- [ ] Redis server running
- [ ] Verify connection from app
- [ ] Set up Redis persistence

### External Services
- [ ] Ollama installed and running: `ollama serve`
- [ ] Pull model: `ollama pull qwen2.5:3b`
- [ ] (Optional) Groq API key for fallback
- [ ] Stripe webhook endpoint configured

## 🔒 Security Verification

### Headers & CORS
- [ ] CORS origins set to specific domains (not "*")
- [ ] Security headers active (X-Frame-Options, CSP, HSTS)
- [ ] Request size limit enforced (10MB max)

### Authentication
- [ ] Password strength validation active
- [ ] Rate limiting configured
- [ ] Zero-trust middleware active
- [ ] Path traversal protection enabled

### Support Bot
- [ ] Abuse pattern filtering active
- [ ] Rate limiting (6 req/min per IP)
- [ ] Message length cap (1500 chars)
- [ ] Prompt injection protection

## ⚡ Performance & Monitoring

### Load Testing
- [ ] Run stress test: `python stress_test.py`
- [ ] Verify rate limiting works (429 responses)
- [ ] Check health endpoint: `/health`

### Monitoring
- [ ] Logging configured (JSON format)
- [ ] Metrics enabled
- [ ] Error tracking (Sentry DSN optional)

## 📦 Deployment Steps

### 1. Build & Deploy
```bash
# Install dependencies
pip install -r requirements.txt

# Run final verification
python final_check.py

# Start with gunicorn (production)
gunicorn -c gunicorn_conf.py apps.api.main:app
```

### 2. SSL & Domain
- [ ] SSL certificate installed
- [ ] Domain pointed to server
- [ ] HTTPS redirects configured

### 3. Stripe Webhook
- [ ] Webhook URL: `https://yourdomain.com/api/v1/subscriptions/webhook`
- [ ] Events enabled: checkout.session.completed, customer.subscription.*, invoice.payment_succeeded
- [ ] Test webhook with Stripe CLI

### 4. Final Verification
- [ ] Health check: `GET /health` returns 200
- [ ] Auth flow: Register → Login → Dashboard works
- [ ] Stripe checkout creates session
- [ ] Support bot responds correctly
- [ ] Rate limiting blocks abuse

## 🎯 Post-Deployment

### Monitoring
- [ ] Check logs for errors
- [ ] Monitor database connections
- [ ] Watch Redis memory usage
- [ ] Track Stripe webhook failures

### Backups
- [ ] Database backups scheduled
- [ ] Redis backups configured
- [ ] Environment variables backed up securely

### Scaling
- [ ] Set up horizontal scaling if needed
- [ ] Configure load balancer
- [ ] Monitor resource usage

## 🚨 Troubleshooting

### Common Issues
- **401 errors**: Check JWT secret key
- **429 errors**: Rate limiting working correctly
- **500 errors**: Check Ollama connection
- **Stripe failures**: Verify webhook secret

### Health Endpoints
- `/health` - Overall system health
- `/status` - Detailed component status
- `/api/v1/subscriptions/plans` - Public plans (no auth)

---

## ✅ Production Ready Checklist

- [ ] All required environment variables set
- [ ] Database migrations applied
- [ ] Security headers verified
- [ ] Rate limiting tested
- [ ] Stripe integration tested
- [ ] Support bot hardened
- [ ] Load testing passed
- [ ] SSL certificate installed
- [ ] Monitoring configured
- [ ] Backups scheduled

When all items checked, the system is production-ready.
