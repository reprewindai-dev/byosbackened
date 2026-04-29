# Veklom Deployment Plan - Hetzner Cloud

## Overview

This document outlines the deployment strategy for the Veklom marketplace backend and frontend on Hetzner Cloud infrastructure.

## Infrastructure Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Hetzner Cloud                             │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │
│  │  Load Balancer│    │  Load Balancer│    │   Database   │    │
│  │   (LB01)      │    │   (LB02)      │    │   (DB01)     │    │
│  │  80.XX.XX.01  │    │  80.XX.XX.02  │    │  10.0.1.10   │    │
│  └──────┬─────────┘    └──────┬─────────┘    └──────┬───────┘    │
│         │                     │                     │            │
│         └─────────────────────┼─────────────────────┘            │
│                               │                                  │
│         ┌─────────────────────┼─────────────────────┐            │
│         │                     │                     │            │
│  ┌──────▼─────────┐  ┌────────▼──────┐  ┌────────▼──────┐      │
│  │  API Server 1  │  │  API Server 2 │  │  API Server 3 │      │
│  │   (APP01)     │  │   (APP02)     │  │   (APP03)     │      │
│  │   10.0.1.11   │  │   10.0.1.12   │  │   10.0.1.13   │      │
│  └───────────────┘  └───────────────┘  └───────────────┘      │
│                                                                  │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐      │
│  │  Redis Cache  │  │  Worker Node  │  │  Worker Node  │      │
│  │   (CACHE01)   │  │   (WORK01)    │  │   (WORK02)    │      │
│  │   10.0.1.20   │  │   10.0.1.21   │  │   10.0.1.22   │      │
│  └───────────────┘  └───────────────┘  └───────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Cloudflare / DNS                            │
│                                                                  │
│   api.veklom.dev ──► LB01 (80.XX.XX.01)                        │
│   app.veklom.dev ──► LB02 (80.XX.XX.02)                        │
│   veklom.dev     ──► Static hosting (Cloudflare Pages)        │
└─────────────────────────────────────────────────────────────────┘
```

## Server Specifications

### Production Environment

| Role | Server Type | Specs | Count | Cost/Month (€) |
|------|-------------|-------|-------|----------------|
| Load Balancer | CX21 | 2 vCPU, 4 GB RAM, 40 GB SSD | 2 | 10.58 |
| API Server | CAX21 (ARM) | 4 vCPU, 8 GB RAM, 80 GB SSD | 3 | 13.13 |
| Database | CCX13 | 2 vCPU, 8 GB RAM, 80 GB NVMe | 1 | 23.65 |
| Redis Cache | CX21 | 2 vCPU, 4 GB RAM, 40 GB SSD | 1 | 5.29 |
| Worker Node | CAX21 (ARM) | 4 vCPU, 8 GB RAM, 80 GB SSD | 2 | 8.76 |
| **Total** | | | **9** | **~61.41** |

### Staging Environment (Reduced)

| Role | Server Type | Specs | Count | Cost/Month (€) |
|------|-------------|-------|-------|----------------|
| API Server | CX21 | 2 vCPU, 4 GB RAM, 40 GB SSD | 1 | 5.29 |
| Database | CX31 | 2 vCPU, 8 GB RAM, 80 GB SSD | 1 | 10.58 |
| Redis | CX11 | 1 vCPU, 2 GB RAM, 20 GB SSD | 1 | 2.65 |
| **Total** | | | **3** | **~18.52** |

## Environment Configuration

### Backend Environment Variables

```bash
# Database
DATABASE_URL=postgresql://veklom:${DB_PASSWORD}@10.0.1.10:5432/veklom

# Redis
REDIS_URL=redis://10.0.1.20:6379/0

# Stripe (Live mode for production)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PUBLISHABLE_KEY=pk_live_...

# Price IDs (Production)
STRIPE_STARTER_PRICE_ID=price_live_...
STRIPE_PRO_PRICE_ID=price_live_...
STRIPE_SOVEREIGN_PRICE_ID=price_live_...
STRIPE_TOKEN_PACK_25_PRICE_ID=price_live_...
STRIPE_TOKEN_PACK_100_PRICE_ID=price_live_...
STRIPE_TOKEN_PACK_500_PRICE_ID=price_live_...
STRIPE_TOKEN_PACK_2000_PRICE_ID=price_live_...

# JWT Secrets
SECRET_KEY=${JWT_SECRET_KEY}
REFRESH_SECRET_KEY=${JWT_REFRESH_SECRET}

# API Keys
API_KEY_SALT=${API_KEY_SALT}

# LLM Configuration
LLM_BASE_URL=http://localhost:11434
LLM_MODEL_DEFAULT=qwen2.5:3b
LLM_FALLBACK=groq
GROQ_API_KEY=${GROQ_API_KEY}
GROQ_MODEL=llama-3.1-8b-instant

# Monitoring
SENTRY_DSN=${SENTRY_DSN}
LOG_LEVEL=INFO

# Feature Flags
ENABLE_TOKEN_WALLET=true
ENABLE_ENTITLEMENT_CHECK=true
ENABLE_TOKEN_DEDUCTION=true
```

### Frontend Environment Variables (Marketplace)

```bash
# API Endpoints
NEXT_PUBLIC_API_URL=https://api.veklom.dev
NEXT_PUBLIC_AUTH_URL=https://api.veklom.dev/api/v1/auth
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...

# Analytics
NEXT_PUBLIC_POSTHOG_KEY=${POSTHOG_KEY}
NEXT_PUBLIC_SENTRY_DSN=${SENTRY_DSN}

# Feature Flags
NEXT_PUBLIC_ENABLE_ANALYTICS=true
NEXT_PUBLIC_ENABLE_STRIPE=true
```

## Deployment Process

### 1. Initial Setup

```bash
# Create Hetzner Cloud project
hcloud context create veklom-production

# Create network
hcloud network create --name veklom-network --ip-range 10.0.0.0/16
hcloud network add-subnet veklom-network --network-zone eu-central --ip-range 10.0.1.0/24 --type server

# Create servers
hcloud server create --name lb01 --type cx21 --image ubuntu-22.04 --network veklom-network
hcloud server create --name app01 --type cax21 --image ubuntu-22.04 --network veklom-network
hcloud server create --name app02 --type cax21 --image ubuntu-22.04 --network veklom-network
hcloud server create --name app03 --type cax21 --image ubuntu-22.04 --network veklom-network
hcloud server create --name db01 --type ccx13 --image ubuntu-22.04 --network veklom-network
hcloud server create --name cache01 --type cx21 --image ubuntu-22.04 --network veklom-network
```

### 2. Database Setup

```bash
# On DB01
sudo apt update && sudo apt install -y postgresql-14 postgresql-contrib

# Configure PostgreSQL
sudo -u postgres psql -c "CREATE DATABASE veklom;"
sudo -u postgres psql -c "CREATE USER veklom WITH PASSWORD '${DB_PASSWORD}';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE veklom TO veklom;"

# Enable required extensions
sudo -u postgres psql -d veklom -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
sudo -u postgres psql -d veklom -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"

# Configure for production
sudo nano /etc/postgresql/14/main/postgresql.conf
# max_connections = 200
# shared_buffers = 2GB
# effective_cache_size = 6GB
# work_mem = 10MB

# Allow internal network access
sudo nano /etc/postgresql/14/main/pg_hba.conf
# host all all 10.0.1.0/24 scram-sha-256
```

### 3. Redis Setup

```bash
# On CACHE01
sudo apt update && sudo apt install -y redis-server

# Configure Redis
sudo nano /etc/redis/redis.conf
# bind 10.0.1.20
# requirepass ${REDIS_PASSWORD}
# maxmemory 2gb
# maxmemory-policy allkeys-lru

sudo systemctl restart redis-server
```

### 4. Application Deployment

```bash
# Build Docker image locally
docker build -t veklom/backend:${VERSION} .
docker tag veklom/backend:${VERSION} ghcr.io/veklom/backend:${VERSION}
docker push ghcr.io/veklom/backend:${VERSION}

# Deploy to app servers
for server in app01 app02 app03; do
  ssh ${server} "docker pull ghcr.io/veklom/backend:${VERSION}"
  ssh ${server} "docker stop veklom-api && docker rm veklom-api"
  ssh ${server} "docker run -d \
    --name veklom-api \
    --restart always \
    -p 8000:8000 \
    --env-file /opt/veklom/.env \
    ghcr.io/veklom/backend:${VERSION}"
done
```

### 5. Load Balancer Configuration (HAProxy)

```bash
# On LB01 and LB02
sudo apt update && sudo apt install -y haproxy

sudo nano /etc/haproxy/haproxy.cfg
```

```haproxy
global
    log /dev/log local0
    maxconn 4096
    user haproxy
    group haproxy
    daemon

defaults
    log global
    mode http
    option httplog
    option dontlognull
    timeout connect 5000
    timeout client 50000
    timeout server 50000
    option forwardfor
    option httpchk GET /health

frontend http-in
    bind *:80
    redirect scheme https if !{ ssl_fc }

frontend https-in
    bind *:443 ssl crt /etc/ssl/certs/veklom.pem
    default_backend api_servers

backend api_servers
    balance roundrobin
    server app01 10.0.1.11:8000 check
    server app02 10.0.1.12:8000 check
    server app03 10.0.1.13:8000 check
```

### 6. SSL Certificate (Let's Encrypt)

```bash
# On LB01
sudo apt install -y certbot
sudo certbot certonly --standalone -d api.veklom.dev

# Copy certs to HAProxy format
sudo cat /etc/letsencrypt/live/api.veklom.dev/fullchain.pem \
  /etc/letsencrypt/live/api.veklom.dev/privkey.pem \
  | sudo tee /etc/ssl/certs/veklom.pem
```

### 7. Database Migration

```bash
# On one app server
ssh app01
docker exec -it veklom-api bash
alembic upgrade head
```

### 8. Monitoring Setup

```bash
# Install Node Exporter on all servers
wget https://github.com/prometheus/node_exporter/releases/download/v1.6.1/node_exporter-1.6.1.linux-amd64.tar.gz
tar xzf node_exporter-1.6.1.linux-amd64.tar.gz
sudo mv node_exporter-1.6.1.linux-amd64/node_exporter /usr/local/bin/

# Create systemd service
sudo tee /etc/systemd/system/node-exporter.service <<EOF
[Unit]
Description=Node Exporter
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/node_exporter
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable node-exporter
sudo systemctl start node-exporter
```

## Marketplace Frontend Deployment

### Cloudflare Pages (Recommended)

```bash
# Build Next.js app
npm run build

# Deploy to Cloudflare Pages
wrangler pages publish out --project-name=veklom-marketplace
```

### Or Static Hosting on Hetzner

```bash
# On LB01
sudo apt install -y nginx

# Configure Nginx for static files
sudo nano /etc/nginx/sites-available/veklom
```

```nginx
server {
    listen 80;
    server_name veklom.dev www.veklom.dev;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name veklom.dev www.veklom.dev;

    ssl_certificate /etc/ssl/certs/veklom.pem;
    ssl_certificate_key /etc/ssl/private/veklom.key;

    root /var/www/veklom;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

## Backup Strategy

### Database Backups

```bash
# Install the Hetzner backup job
sudo apt-get update
sudo apt-get install -y awscli postgresql-client python3
sudo install -m 0755 /path/to/backend/infra/scripts/backup-postgres.sh /opt/scripts/backup-postgres.sh
sudo install -m 0755 /path/to/backend/infra/scripts/install-hetzner-backup.sh /opt/scripts/install-hetzner-backup.sh

# Fill in /etc/veklom/backup.env with:
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# AWS_DEFAULT_REGION=us-east-1
# S3_BACKUP_BUCKET=veklom-db-backups
# DATABASE_URL=postgresql://veklom:...

# Daily backup behavior:
# - pg_dump the live Postgres database
# - gzip the dump
# - upload to s3://veklom-db-backups/postgres/<timestamp>/
# - remove the local copy
# - delete S3 objects older than 7 days
```

### Cron Schedule

```bash
# Daily at 2 AM
0 2 * * * root /opt/scripts/backup-postgres.sh
```

## Security Checklist

- [ ] Firewall rules: Only LB IPs exposed, internal network isolated
- [ ] SSH key-based authentication only
- [ ] Fail2ban for brute force protection
- [ ] Regular security updates: `unattended-upgrades`
- [ ] Database: SSL connections required
- [ ] API: Rate limiting enabled
- [ ] Secrets: Stored in HashiCorp Vault or environment
- [ ] Logs: Forwarded to centralized logging
- [ ] WAF: Cloudflare or ModSecurity on LB

## Rollback Plan

```bash
# Quick rollback to previous version
VERSION=previous
for server in app01 app02 app03; do
  ssh ${server} "docker stop veklom-api && docker rm veklom-api"
  ssh ${server} "docker run -d --name veklom-api --restart always -p 8000:8000 --env-file /opt/veklom/.env ghcr.io/veklom/backend:${VERSION}"
done

# Database rollback (if migration failed)
alembic downgrade -1
```

## Cost Optimization Tips

1. **ARM Servers (CAX)**: 40% cheaper than x86 with comparable performance
2. **Reserved IPs**: Use Hetzner floating IPs for easy failover
3. **Object Storage**: Use Cloudflare R2 (free egress) for backups
4. **Auto-scaling**: Use Hetzner API to scale workers based on queue depth
5. **Development**: Use staging environment, destroy/recreate as needed

## Support Contacts

- **Hetzner Support**: support@hetzner.com
- **Cloudflare Support**: Dashboard → Get Help
- **Veklom On-Call**: oncall@veklom.com

---

*Version: 1.0*
*Last Updated: 2026-04-27*
