# Render.com Deployment Guide

Complete guide for deploying the BYOS AI Backend to Render.com using `render.yaml`.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pre-Deployment Setup](#pre-deployment-setup)
3. [Render.com Account Setup](#rendercom-account-setup)
4. [Deploying Services](#deploying-services)
5. [Configuring Environment Variables](#configuring-environment-variables)
6. [Running Database Migrations](#running-database-migrations)
7. [Post-Deployment Verification](#post-deployment-verification)
8. [Setting Up S3 Storage](#setting-up-s3-storage)
9. [Monitoring & Maintenance](#monitoring--maintenance)
10. [Troubleshooting](#troubleshooting)
11. [Scaling & Upgrades](#scaling--upgrades)

---

## Prerequisites

Before deploying to Render.com, ensure you have:

- ✅ **Render.com account** (sign up at [render.com](https://render.com))
- ✅ **GitHub/GitLab/Bitbucket repository** with your code
- ✅ **API Keys** ready (optional):
  - Groq API key (for cloud fallback)
  - SERP API key (for search)
  - OpenAI API key (for external provider)
  - HuggingFace API key (for external provider)
- ✅ **S3-compatible storage** account (AWS S3, Backblaze B2, DigitalOcean Spaces, etc.)
- ✅ **Domain name** (optional, Render provides free subdomain)

---

## Pre-Deployment Setup

### 1. Generate Security Keys

```bash
# Generate SECRET_KEY (32-byte hex string)
openssl rand -hex 32

# Save this value - you'll need it for environment variables
```

### 2. Prepare S3 Storage

Choose one of these options:

**Option A: AWS S3** (Recommended for production)
- Create an S3 bucket
- Create IAM user with S3 access
- Get access key ID and secret access key
- Note the region (e.g., `us-east-1`)

**Option B: Backblaze B2**
- Create B2 bucket
- Create application key
- Use endpoint: `https://s3.us-west-000.backblazeb2.com` (adjust region)

**Option C: DigitalOcean Spaces**
- Create Space
- Generate access keys
- Use endpoint: `https://<region>.digitaloceanspaces.com`

### 3. Verify Repository

Ensure your repository contains:
- ✅ `render.yaml` file in the root directory
- ✅ `infra/docker/Dockerfile.api`
- ✅ `infra/docker/Dockerfile.worker`
- ✅ `pyproject.toml` with dependencies
- ✅ `alembic.ini` for database migrations

---

## Render.com Account Setup

### 1. Create Render Account

1. Go to [render.com](https://render.com) and sign up
2. Verify your email address
3. Connect your Git provider (GitHub/GitLab/Bitbucket)

### 2. Link Repository

1. In Render dashboard, click **"New +"** → **"Blueprint"**
2. Connect your repository
3. Render will detect `render.yaml` automatically
4. Select the repository and branch (usually `main` or `master`)

---

## Deploying Services

### Step 1: Deploy from Blueprint

1. Render will parse `render.yaml` and show you all services to create:
   - PostgreSQL database (`byos-ai-db`)
   - Redis instance (`byos-ai-redis`)
   - Web service (`byos-ai-api`)
   - Worker service (`byos-ai-worker`)

2. Review the services and click **"Apply"**

3. Render will start creating services in this order:
   - Database (PostgreSQL)
   - Redis
   - API web service
   - Worker service

**Note**: The first deployment may take 10-15 minutes as Docker images are built.

### Step 2: Monitor Deployment

Watch the deployment logs in Render dashboard:
- Click on each service to see build/deploy logs
- API service will show Docker build progress
- Worker service will show similar build logs

**Expected output**:
```
Building Docker image...
Step 1/7 : FROM python:3.11-slim
...
Successfully built <image-id>
Starting service...
```

---

## Configuring Environment Variables

After services are created, configure environment variables that are marked `sync: false` in `render.yaml`.

### For API Service (`byos-ai-api`)

1. Go to **Dashboard** → **byos-ai-api** → **Environment**
2. Add the following variables:

#### Security (Required)
```
SECRET_KEY=<your-generated-secret-key>
ENCRYPTION_KEY=<optional-or-same-as-secret-key>
```

#### S3 Storage (Required)
```
S3_ENDPOINT_URL=https://s3.amazonaws.com  # Or your S3-compatible endpoint
S3_ACCESS_KEY_ID=<your-access-key-id>
S3_SECRET_ACCESS_KEY=<your-secret-access-key>
```

#### AI Providers (Optional)
Local inference via Ollama works without any API keys. Set these only if you want external providers:
```
GROQ_API_KEY=<your-groq-key>  # For fallback when Ollama fails
OPENAI_API_KEY=<your-openai-key>  # For GPT-4/Whisper provider
HUGGINGFACE_API_KEY=<your-hf-token>  # For HF inference provider
SERPAPI_KEY=<your-serpapi-key>  # For search functionality
```

#### CORS (Update for production)
```
CORS_ORIGINS=["https://your-frontend-domain.com"]  # Replace with your frontend URL
```

#### Optional Observability
```
SENTRY_DSN=<your-sentry-dsn>  # Optional, for error tracking
```

### For Worker Service (`byos-ai-worker`)

1. Go to **Dashboard** → **byos-ai-worker** → **Environment**
2. Add the **same environment variables** as the API service:
   - `SECRET_KEY`
   - `ENCRYPTION_KEY`
   - `S3_ENDPOINT_URL`
   - `S3_ACCESS_KEY_ID`
   - `S3_SECRET_ACCESS_KEY`
   - `GROQ_API_KEY` (recommended for fallback)
   - `HUGGINGFACE_API_KEY` (if using HF)
   - `OPENAI_API_KEY` (if using OpenAI)
   - `SERPAPI_KEY` (if using search)

**Important**: Both services need identical environment variables for consistency.

### Verify Environment Variables

After adding variables, Render will automatically redeploy services. Wait for deployment to complete.

---

## Running Database Migrations

After the API service is deployed and environment variables are set:

### Option 1: Using Render Shell (Recommended)

1. Go to **Dashboard** → **byos-ai-api** → **Shell**
2. Run migrations:
   ```bash
   alembic upgrade head
   ```
3. Verify migration:
   ```bash
   alembic current
   ```

### Option 2: Using Local Alembic

If you have local access configured:

```bash
# Set DATABASE_URL to Render's internal database URL
export DATABASE_URL=<render-database-internal-url>

# Run migrations
alembic upgrade head
```

**Note**: Use Render's internal database URL (found in database service → **Info** → **Internal Database URL**) for migrations.

---

## Post-Deployment Verification

### 1. Check Service Health

```bash
# Get your API service URL from Render dashboard
curl https://byos-ai-api.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "database": "connected",
  "redis": "connected"
}
```

### 2. Verify API Documentation

Visit: `https://byos-ai-api.onrender.com/api/v1/docs`

You should see the Swagger UI with all available endpoints.

### 3. Check Worker Logs

1. Go to **Dashboard** → **byos-ai-worker** → **Logs**
2. Look for:
   ```
   celery@hostname ready
   ```

### 4. Test API Endpoint

```bash
# Test health endpoint
curl https://byos-ai-api.onrender.com/api/v1/health

# Test with authentication (if configured)
curl -H "Authorization: Bearer <token>" \
     https://byos-ai-api.onrender.com/api/v1/jobs
```

### 5. Verify Database Connection

In Render Shell for API service:
```bash
python -c "
from db.session import SessionLocal
db = SessionLocal()
result = db.execute('SELECT 1')
print('Database connected:', result.fetchone())
"
```

---

## Setting Up S3 Storage

### AWS S3 Configuration

1. **Create S3 Bucket**:
   - Go to AWS S3 Console
   - Create bucket: `byos-ai` (or your preferred name)
   - Choose region (e.g., `us-east-1`)
   - Disable public access (recommended)

2. **Create IAM User**:
   - Go to IAM → Users → Create user
   - Attach policy: `AmazonS3FullAccess` (or create custom policy)
   - Create access keys
   - Save Access Key ID and Secret Access Key

3. **Configure in Render**:
   ```
   S3_ENDPOINT_URL=https://s3.amazonaws.com
   S3_ACCESS_KEY_ID=<iam-access-key-id>
   S3_SECRET_ACCESS_KEY=<iam-secret-key>
   S3_BUCKET_NAME=byos-ai
   S3_REGION=us-east-1
   S3_USE_SSL=true
   ```

### Backblaze B2 Configuration

1. **Create B2 Bucket**:
   - Go to Backblaze B2 Console
   - Create bucket: `byos-ai`
   - Note endpoint URL (e.g., `https://s3.us-west-000.backblazeb2.com`)

2. **Create Application Key**:
   - Go to App Keys → Add New Application Key
   - Save Key ID and Application Key

3. **Configure in Render**:
   ```
   S3_ENDPOINT_URL=https://s3.us-west-000.backblazeb2.com
   S3_ACCESS_KEY_ID=<b2-key-id>
   S3_SECRET_ACCESS_KEY=<b2-application-key>
   S3_BUCKET_NAME=byos-ai
   S3_REGION=us-west-000
   S3_USE_SSL=true
   ```

### DigitalOcean Spaces Configuration

1. **Create Space**:
   - Go to DigitalOcean → Spaces
   - Create Space: `byos-ai`
   - Choose region (e.g., `nyc3`)

2. **Generate Access Keys**:
   - Go to API → Spaces Keys
   - Generate new key pair

3. **Configure in Render**:
   ```
   S3_ENDPOINT_URL=https://nyc3.digitaloceanspaces.com
   S3_ACCESS_KEY_ID=<do-spaces-key>
   S3_SECRET_ACCESS_KEY=<do-spaces-secret>
   S3_BUCKET_NAME=byos-ai
   S3_REGION=nyc3
   S3_USE_SSL=true
   ```

---

## Monitoring & Maintenance

### 1. View Logs

**API Service**:
- Dashboard → **byos-ai-api** → **Logs**
- Real-time logs with search capability

**Worker Service**:
- Dashboard → **byos-ai-worker** → **Logs**
- Monitor Celery task execution

### 2. Set Up Alerts

1. Go to **Dashboard** → **Settings** → **Alerts**
2. Configure:
   - Email alerts for service failures
   - Slack webhook (optional)
   - PagerDuty integration (optional)

### 3. Monitor Metrics

Render provides built-in metrics:
- **CPU Usage**
- **Memory Usage**
- **Request Rate**
- **Response Times**

Access via: Dashboard → **byos-ai-api** → **Metrics**

### 4. Health Checks

Render automatically monitors:
- Health endpoint: `/health`
- Service availability
- Automatic restarts on failure

### 5. Database Backups

Render PostgreSQL includes:
- **Automatic daily backups** (on paid plans)
- **Point-in-time recovery** (on standard plans)
- Access backups via: Dashboard → **byos-ai-db** → **Backups**

### 6. Update Deployment

When you push to your repository:

1. Render detects changes automatically
2. Triggers new deployment
3. Builds new Docker images
4. Deploys with zero downtime (on standard plans)

**Manual Deploy**:
- Dashboard → **byos-ai-api** → **Manual Deploy** → **Deploy latest commit**

---

## Troubleshooting

### Service Won't Start

**Symptoms**: Service shows "Failed" status

**Solutions**:
1. Check logs: Dashboard → Service → **Logs**
2. Verify environment variables are set correctly
3. Check Dockerfile paths in `render.yaml`
4. Verify `DATABASE_URL` and `REDIS_URL` are auto-populated

**Common Issues**:
```
Error: DATABASE_URL not set
→ Check that database service is created and linked
```

```
Error: Module not found
→ Verify pyproject.toml dependencies are correct
```

### Database Connection Errors

**Symptoms**: API logs show "database connection failed"

**Solutions**:
1. Verify database is running: Dashboard → **byos-ai-db** → **Status**
2. Check `DATABASE_URL` uses internal URL (not external)
3. Verify database name matches: `byos_ai`
4. Test connection in Shell:
   ```bash
   python -c "from db.session import SessionLocal; db = SessionLocal(); print('Connected')"
   ```

### Worker Not Processing Jobs

**Symptoms**: Jobs queued but not processed

**Solutions**:
1. Check worker logs: Dashboard → **byos-ai-worker** → **Logs**
2. Verify Redis connection:
   ```bash
   # In worker shell
   python -c "import redis; r = redis.from_url('$REDIS_URL'); print(r.ping())"
   ```
3. Verify `CELERY_BROKER_URL` matches `REDIS_URL`
4. Check worker is running: Look for "celery@hostname ready" in logs

### S3 Connection Errors

**Symptoms**: File uploads fail, S3 errors in logs

**Solutions**:
1. Verify S3 credentials are correct
2. Check bucket exists and is accessible
3. Verify endpoint URL format:
   - AWS: `https://s3.amazonaws.com` or `https://s3.<region>.amazonaws.com`
   - B2: `https://s3.<region>.backblazeb2.com`
   - DO: `https://<region>.digitaloceanspaces.com`
4. Test S3 connection:
   ```bash
   python -c "
   import boto3
   s3 = boto3.client('s3',
       endpoint_url='$S3_ENDPOINT_URL',
       aws_access_key_id='$S3_ACCESS_KEY_ID',
       aws_secret_access_key='$S3_SECRET_ACCESS_KEY'
   )
   print(s3.list_buckets())
   "
   ```

### High Memory Usage

**Symptoms**: Service restarts frequently, memory warnings

**Solutions**:
1. Upgrade service plan: Dashboard → Service → **Settings** → **Change Plan**
2. Optimize Docker image (multi-stage builds)
3. Review worker concurrency:
   ```bash
   # In Dockerfile.worker, adjust Celery workers
   CMD ["celery", "-A", "apps.worker.worker", "worker", "--concurrency=2", "--loglevel=info"]
   ```

### Slow Build Times

**Symptoms**: Deployments take >15 minutes

**Solutions**:
1. Use Docker layer caching (Render does this automatically)
2. Optimize Dockerfile (order dependencies before code)
3. Use `.dockerignore` to exclude unnecessary files
4. Consider using pre-built base images

---

## Scaling & Upgrades

### Upgrade Service Plans

**When to Upgrade**:
- High traffic volume
- Memory/CPU limits reached
- Need better performance

**How to Upgrade**:
1. Dashboard → Service → **Settings** → **Change Plan**
2. Select higher tier (e.g., `standard-0` → `standard-1`)
3. Render automatically migrates (zero downtime)

### Scale Workers

To handle more background jobs:

1. **Option A: Increase Worker Concurrency**
   - Edit `Dockerfile.worker`
   - Change `--concurrency=1` to `--concurrency=4`
   - Redeploy

2. **Option B: Add Additional Worker Services**
   - Duplicate worker service in `render.yaml`
   - Name: `byos-ai-worker-2`
   - Same configuration, different instance

### Database Scaling

**Upgrade Database Plan**:
- Dashboard → **byos-ai-db** → **Settings** → **Change Plan**
- Higher plans = more RAM, CPU, storage
- Automatic migration (may have brief downtime)

**Read Replicas** (Enterprise):
- Create read replica for read-heavy workloads
- Configure in database settings

### Horizontal Scaling (Multiple API Instances)

Render automatically handles:
- Load balancing across instances
- Health checks
- Automatic failover

To enable:
1. Dashboard → **byos-ai-api** → **Settings**
2. Enable **Auto-Scaling** (on standard plans)
3. Set min/max instances

---

## Cost Optimization

### Render Pricing Tips

1. **Use Starter Plans for Development**
   - Free tier available (with limitations)
   - Upgrade only when needed

2. **Optimize Worker Resources**
   - Use smaller worker instances if jobs are lightweight
   - Scale down during low-traffic periods

3. **Database Optimization**
   - Use starter plan for development
   - Upgrade only when hitting limits
   - Monitor query performance

4. **S3 Storage Costs**
   - Use lifecycle policies to archive old files
   - Consider Backblaze B2 for lower costs
   - Enable compression for stored files

### Monitoring Costs

1. Dashboard → **Billing** → **Usage**
2. Track:
   - Service hours
   - Database storage
   - Bandwidth usage
3. Set up billing alerts

---

## Custom Domain Setup

### Add Custom Domain

1. Dashboard → **byos-ai-api** → **Settings** → **Custom Domains**
2. Add domain: `api.yourdomain.com`
3. Render provides DNS records to add:
   ```
   Type: CNAME
   Name: api
   Value: <render-provided-hostname>
   ```
4. Add DNS record in your domain registrar
5. Render automatically provisions SSL certificate

### SSL Certificate

- Render provides **free SSL certificates** via Let's Encrypt
- Automatic renewal
- HTTPS enforced by default

---

## Security Best Practices

### 1. Environment Variables

- ✅ Never commit secrets to repository
- ✅ Use Render's environment variable encryption
- ✅ Rotate secrets regularly
- ✅ Use different secrets for staging/production

### 2. Database Security

- ✅ Use Render's internal database URLs (not exposed)
- ✅ Enable database backups
- ✅ Restrict database access to services only

### 3. API Security

- ✅ Set `DEBUG=false` in production
- ✅ Configure `CORS_ORIGINS` with specific domains
- ✅ Use strong `SECRET_KEY` (32+ bytes)
- ✅ Enable rate limiting (configure in API code)

### 4. Worker Security

- ✅ Same security practices as API
- ✅ Isolate worker from public internet
- ✅ Monitor worker logs for suspicious activity

---

## Rollback Procedure

If deployment causes issues:

### Quick Rollback

1. Dashboard → **byos-ai-api** → **Deploys**
2. Find previous successful deployment
3. Click **"Rollback to this deploy"**
4. Confirm rollback

### Database Rollback

If migration caused issues:

1. Connect to database via Shell
2. Run:
   ```bash
   alembic downgrade -1  # Rollback one migration
   # or
   alembic downgrade <revision>  # Rollback to specific revision
   ```

---

## Support & Resources

### Render Documentation
- [Render Docs](https://render.com/docs)
- [Render Community](https://community.render.com)
- [Render Status](https://status.render.com)

### Application-Specific
- Check logs first: Dashboard → Service → **Logs**
- Review `render.yaml` configuration
- Verify environment variables

### Emergency Contacts
- Render Support: support@render.com
- Render Status Page: status.render.com

---

## Deployment Checklist

Use this checklist for each deployment:

### Pre-Deployment
- [ ] All environment variables prepared
- [ ] S3 storage configured and tested
- [ ] Optional API keys obtained (Groq, HuggingFace, OpenAI, SERP)
- [ ] `SECRET_KEY` generated
- [ ] Repository pushed to Git

### Deployment
- [ ] Services created from `render.yaml`
- [ ] Environment variables configured
- [ ] Database migrations run
- [ ] Health check passes
- [ ] API documentation accessible

### Post-Deployment
- [ ] Test API endpoints
- [ ] Verify worker processing jobs
- [ ] Check logs for errors
- [ ] Monitor metrics
- [ ] Set up alerts
- [ ] Document deployment

---

## Next Steps

After successful deployment:

1. **Set up monitoring**: Configure alerts and dashboards
2. **Create initial workspace**: Use API to create first workspace
3. **Test workflows**: Verify transcription, extraction, etc.
4. **Configure backups**: Ensure database backups are enabled
5. **Document URLs**: Save service URLs for team
6. **Set up CI/CD**: Configure automatic deployments on push

---

**Remember**: This backend is designed to be portable. You can move it from Render to any other platform in hours, not weeks.
