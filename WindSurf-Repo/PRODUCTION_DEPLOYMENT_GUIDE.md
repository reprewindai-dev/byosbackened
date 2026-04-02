# Production Deployment Guide
# ===========================

## Overview
This guide covers the complete production deployment of the SOVEREIGN AI SAAS STACK v1.0.

## Prerequisites

### Infrastructure Requirements
- **CPU**: Minimum 4 cores (recommended 8+ cores)
- **Memory**: Minimum 8GB RAM (recommended 16GB+)
- **Storage**: Minimum 100GB SSD (recommended 500GB+)
- **Network**: 1Gbps connection recommended

### Software Requirements
- Docker 20.10+
- Docker Compose 2.0+
- Git
- SSL certificates (for HTTPS)

### External Services
- PostgreSQL 15+ (or managed database service)
- Redis 7+ (or managed Redis service)
- Domain name with DNS configuration
- SSL certificates (Let's Encrypt recommended)

## Quick Start

### 1. Clone Repository
```bash
git clone <repository-url>
cd byos-ai-backend
```

### 2. Configure Environment
```bash
# Copy production environment template
cp .env.production .env.local

# Edit configuration
nano .env.local
```

**Critical Configuration Items:**
- `SECRET_KEY`: Generate a secure 64-character random key
- `POSTGRES_PASSWORD`: Set a strong database password
- `REDIS_PASSWORD`: Set a strong Redis password
- `DATABASE_URL`: Update with your PostgreSQL connection string
- `STRIPE_SECRET_KEY`: Add your live Stripe keys
- `HUGGINGFACE_API_KEY`: Add your HuggingFace API key

### 3. Generate SSL Certificates
```bash
# Create SSL directory
mkdir -p infra/docker/ssl

# Generate self-signed certificates (for testing)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout infra/docker/ssl/key.pem \
    -out infra/docker/ssl/cert.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# OR use Let's Encrypt for production
certbot certonly --standalone -d your-domain.com
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem infra/docker/ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem infra/docker/ssl/key.pem
```

### 4. Deploy with Docker Compose
```bash
# Build and start all services
docker-compose -f docker-compose.production.yml up --build -d

# Check service status
docker-compose -f docker-compose.production.yml ps

# View logs
docker-compose -f docker-compose.production.yml logs -f api
```

### 5. Run Database Migrations
```bash
# Enter API container
docker-compose -f docker-compose.production.yml exec api bash

# Run migrations
alembic upgrade head

# Exit container
exit
```

### 6. Verify Deployment
```bash
# Health check
curl -f https://your-domain.com/health

# API documentation
curl -f https://your-domain.com/api/v1/docs

# Dashboard access
https://your-domain.com/sovereign_dashboard.html
```

## Detailed Configuration

### Database Setup

#### Option 1: Managed PostgreSQL (Recommended)
```bash
# Example for AWS RDS
# Create RDS instance with PostgreSQL 15
# Configure security group to allow Docker network access
# Update DATABASE_URL in .env.local:
DATABASE_URL=postgresql://username:password@rds-endpoint:5432/sovereign_production
```

#### Option 2: Self-Hosted PostgreSQL
```bash
# The Docker Compose file includes PostgreSQL
# Ensure persistent volume is configured
# Backup strategy implemented
```

### Redis Setup

#### Option 1: Managed Redis (Recommended)
```bash
# Example for AWS ElastiCache
# Create Redis cluster
# Update REDIS_URL in .env.local:
REDIS_URL=redis://:password@cache-endpoint:6379/0
```

#### Option 2: Self-Hosted Redis
```bash
# Included in Docker Compose
# Configure persistence and security
```

### SSL/TLS Configuration

#### Nginx Configuration
```nginx
# File: infra/docker/nginx/nginx.conf
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    location / {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Monitoring Setup

#### Prometheus Configuration
```yaml
# File: infra/docker/prometheus/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'sovereign-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
```

#### Grafana Dashboards
- Access: https://your-domain.com:3000
- Default credentials: admin / (GRAFANA_PASSWORD)
- Pre-configured dashboards included

## Security Configuration

### Firewall Rules
```bash
# Allow only necessary ports
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable
```

### Security Headers
```nginx
# Add to Nginx configuration
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
```

### Rate Limiting
```bash
# Configure in application
RATE_LIMIT_PER_MINUTE=1000
RATE_LIMIT_BURST=2000
```

## Backup Strategy

### Database Backups
```bash
# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)

docker-compose -f docker-compose.production.yml exec postgres \
    pg_dump -U sovereign_user sovereign_production > "$BACKUP_DIR/backup_$DATE.sql"

# Keep last 30 days
find $BACKUP_DIR -name "backup_*.sql" -mtime +30 -delete
```

### File Backups
```bash
# Backup application data
tar -czf /backups/data_$(date +%Y%m%d).tar.gz /app/data /app/logs
```

## Performance Optimization

### Database Optimization
```sql
-- PostgreSQL performance settings
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
SELECT pg_reload_conf();
```

### Application Optimization
```bash
# Worker processes
WORKERS=4

# Connection pooling
MAX_CONNECTIONS=100

# Cache settings
CACHE_TTL=300
CACHE_MAX_SIZE=1000
```

## Scaling Configuration

### Horizontal Scaling
```yaml
# Docker Compose scaling
services:
  api:
    deploy:
      replicas: 3
  worker:
    deploy:
      replicas: 2
```

### Load Balancer Configuration
```nginx
upstream sovereign_api {
    server api_1:8000;
    server api_2:8000;
    server api_3:8000;
}

server {
    location / {
        proxy_pass http://sovereign_api;
    }
}
```

## Troubleshooting

### Common Issues

#### Database Connection Failed
```bash
# Check database status
docker-compose -f docker-compose.production.yml exec postgres pg_isready

# Check logs
docker-compose -f docker-compose.production.yml logs postgres

# Verify connection string
echo $DATABASE_URL
```

#### Redis Connection Failed
```bash
# Check Redis status
docker-compose -f docker-compose.production.yml exec redis redis-cli ping

# Check logs
docker-compose -f docker-compose.production.yml logs redis
```

#### Application Not Starting
```bash
# Check application logs
docker-compose -f docker-compose.production.yml logs api

# Check environment variables
docker-compose -f docker-compose.production.yml exec api env | grep -E "(DATABASE|REDIS|SECRET)"

# Verify health endpoint
curl -f http://localhost:8000/health
```

### Performance Issues

#### Slow Queries
```bash
# Enable query logging
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_min_duration_statement = 1000;

# Check slow queries
docker-compose -f docker-compose.production.yml exec api python -c "
from core.performance.optimization import db_optimizer
import asyncio
result = asyncio.run(db_optimizer.analyze_slow_queries())
print(result)
"
```

#### High Memory Usage
```bash
# Check memory usage
docker stats

# Monitor application
curl -f http://localhost:8000/api/v1/dashboard/system-status
```

## Maintenance

### Rolling Updates
```bash
# Update without downtime
docker-compose -f docker-compose.production.yml up --no-deps api
docker-compose -f docker-compose.production.yml up --no-deps worker
```

### Health Monitoring
```bash
# Continuous health check
while true; do
    curl -f http://localhost:8000/health || echo "Health check failed"
    sleep 30
done
```

### Log Rotation
```bash
# Configure logrotate
cat > /etc/logrotate.d/sovereign-ai << EOF
/app/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 sovereign sovereign
}
EOF
```

## Support and Monitoring

### Monitoring Dashboards
- **Grafana**: https://your-domain.com:3000
- **Prometheus**: https://your-domain.com:9090
- **Kibana**: https://your-domain.com:5601 (if ELK stack enabled)

### Alert Configuration
```yaml
# Prometheus alert rules
groups:
  - name: sovereign-ai
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
```

### Support Contacts
- **Technical Support**: support@sovereign-ai.com
- **Documentation**: https://docs.sovereign-ai.com
- **Status Page**: https://status.sovereign-ai.com

## Security Checklist

- [ ] SSL certificates installed and valid
- [ ] Firewall configured
- [ ] Database credentials secure
- [ ] Redis authentication enabled
- [ ] Rate limiting configured
- [ ] Security headers implemented
- [ ] Backup strategy in place
- [ ] Monitoring and alerting configured
- [ ] Log rotation configured
- [ ] Access controls implemented

## Production Deployment Complete

Once all steps are completed, your SOVEREIGN AI SAAS STACK will be:
- ✅ Fully deployed with PostgreSQL and Redis
- ✅ Secured with SSL/TLS encryption
- ✅ Monitored with Prometheus and Grafana
- ✅ Backed up with automated backups
- ✅ Scaled for production workloads
- ✅ Ready for enterprise usage

For additional support, contact the SOVEREIGN AI team.
