# Digital Ocean LLM VPS Deployment Guide

## Overview

This guide provides comprehensive deployment instructions for the Sovereign AI SaaS Stack on Digital Ocean infrastructure with LLM capabilities.

## Deployment Options

### 1. GPU Droplet (Recommended for LLM Workloads)

**Best for:** Production LLM inference, model fine-tuning, high-performance AI workloads

**Requirements:**
- Digital Ocean account with GPU droplet access
- SSH key configured
- Domain name (optional)

**Hardware:**
- GPU Droplet (g6-standard-4 or higher)
- NVIDIA A10G GPU
- 16GB+ RAM
- 200GB+ SSD storage

### 2. Standard Droplet

**Best for:** Development, small-scale deployments, CPU-based models

**Hardware:**
- Standard Droplet (s-4vcpu-8gb or higher)
- 8GB+ RAM
- 100GB+ SSD storage

### 3. App Platform (Serverless)

**Best for:** Quick deployments, low traffic, no GPU requirements

**Limitations:**
- No GPU support
- Resource constraints
- Less control over infrastructure

## Quick Start

### Prerequisites

1. **Install doctl CLI**
```bash
# macOS
brew install doctl

# Linux
curl -sL https://github.com/digitalocean/doctl/releases/latest/download/doctl-$(uname -s)-$(uname -m).tar.gz | tar xz
sudo mv doctl /usr/local/bin
```

2. **Authenticate with Digital Ocean**
```bash
doctl auth init
```

3. **Generate SSH Key** (if not already done)
```bash
ssh-keygen -t rsa -b 4096
doctl compute ssh-key import --ssh-key-name sovereign-ai-key --public-key-file ~/.ssh/id_rsa.pub
```

### GPU Droplet Deployment

1. **Setup Environment**
```bash
# Clone repository
git clone https://github.com/your-username/sovereign-ai-saas.git
cd sovereign-ai-saas

# Setup environment variables
chmod +x setup-do-env.sh
./setup-do-env.sh gpu your-domain.com
```

2. **Deploy**
```bash
chmod +x deploy-gpu-droplet.sh
./deploy-gpu-droplet.sh
```

3. **Verify Deployment**
```bash
# Check GPU status
ssh root@your-droplet-ip 'nvidia-smi'

# Check services
ssh root@your-droplet-ip 'docker-compose ps'

# Check logs
ssh root@your-droplet-ip 'docker-compose logs -f api'
```

### Standard Droplet Deployment

1. **Setup Environment**
```bash
./setup-do-env.sh standard your-domain.com
```

2. **Deploy (Hardened Automation)**
```bash
chmod +x deploy-digital-ocean.sh
./deploy-digital-ocean.sh \
  --ssh-key "<fingerprint>" \
  --droplet-name sovereign-ai-prod \
  --region nyc3 \
  --size g6-standard-4 \
  --env-file .env.production \
  --compose-file docker-compose.production.yml
```

> The script provisions the droplet, attaches firewalls, syncs your secrets, builds containers, executes migrations, and enables a systemd unit for crash-safe restarts.

### App Platform Deployment

1. **Setup Environment**
```bash
./setup-do-env.sh app-platform your-domain.com
```

2. **Deploy**
```bash
chmod +x deploy-app-platform.sh
./deploy-app-platform.sh
```

## Automated Digital Ocean Deployment Script

`deploy-digital-ocean.sh` exposes full production controls:

| Flag | Description |
| --- | --- |
| `--ssh-key` | **Required.** DigitalOcean SSH key fingerprint. |
| `--droplet-name`, `--region`, `--size`, `--image` | Infrastructure sizing & placement. Defaults target gpu-ready g6-standard-4 in NYC3. |
| `--env-file`, `--compose-file` | Source .env (must contain live Stripe keys) and compose manifest to ship. |
| `--repo-url`, `--branch` | Git remote + branch pulled onto the droplet before building. |
| `--app-host`, `--api-host` | Override public URLs (otherwise nip.io based on droplet IP). |
| `--tags`, `--firewall-name`, `--skip-firewall`, `--skip-backups` | DigitalOcean governance knobs for tagging, backups, and firewall management. |
| `--doctl-bin`, `--ssh-user` | Allow custom binary paths or non-root bootstrap accounts. |

### Execution Flow

1. **Validation:** ensures doctl/ssh/scp availability and blocks deployments with placeholder Stripe keys.
2. **Provisioning:** creates (or reuses) the droplet, enables monitoring/backups, and attaches a firewall covering 22/80/443/3000/9090/5601.
3. **Hardening:** updates the OS, installs Docker/Compose, enables UFW + Fail2Ban, and locks down the `/opt/sovereign-ai` workspace.
4. **Secrets Sync:** pushes `.env.production` + compose manifest, stamps build metadata, and rewrites FRONTEND/API URLs.
5. **Rollout:** performs `docker compose build/up`, runs Alembic migrations, and registers a systemd unit for auto-restarts.
6. **Output:** surfaces IP, HTTPS endpoints, monitoring URLs, and artifact metadata for the operations log.

> **Billing enforcement:** deployment halts if `STRIPE_SECRET_KEY` or `STRIPE_PUBLISHABLE_KEY` still contain placeholder tokens, guaranteeing every environment is revenue-connected.

## Configuration

### Environment Variables

Key environment variables in `.env.production`:

```bash
# Security
SECRET_KEY=your-64-character-secret-key
AI_CITIZENSHIP_SECRET=your-ai-citizenship-secret

# Database
POSTGRES_PASSWORD=your-secure-postgres-password
DATABASE_URL=postgresql://sovereign_user:password@postgres:5432/sovereign_production

# Redis
REDIS_PASSWORD=your-secure-redis-password
REDIS_URL=redis://:password@redis:6379/0

# AI Services
HUGGINGFACE_API_KEY=hf_your-huggingface-token
OPENAI_API_KEY=sk-your-openai-key

# Billing
STRIPE_SECRET_KEY=sk_live_your-stripe-secret
STRIPE_PUBLISHABLE_KEY=pk_live_your-stripe-publishable

# GPU Configuration (GPU droplets only)
CUDA_VISIBLE_DEVICES=0
GPU_MEMORY_FRACTION=0.8
MODEL_CACHE_DIR=/app/models
```

### SSL Configuration

1. **Generate SSL Certificate**
```bash
# Install certbot on droplet
ssh root@your-droplet-ip 'apt install certbot python3-certbot-nginx'

# Generate certificate
ssh root@your-droplet-ip 'certbot --nginx -d your-domain.com'
```

2. **Update Nginx Configuration**
```bash
# SSL certs will be automatically configured by certbot
# Location: /etc/letsencrypt/live/your-domain.com/
```

## Monitoring

### Setup Monitoring Stack

1. **Deploy Monitoring Services**
```bash
chmod +x setup-monitoring.sh
./setup-monitoring.sh

# Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d
```

2. **Access Monitoring Dashboards**
- **Grafana:** http://your-droplet-ip:3000
  - Username: admin
  - Password: Set in `GRAFANA_PASSWORD` env var
- **Prometheus:** http://your-droplet-ip:9090
- **Loki:** http://your-droplet-ip:3100

### Key Metrics to Monitor

- **API Response Time**
- **GPU Utilization** (GPU droplets)
- **Memory Usage**
- **Database Connections**
- **Request Rate**
- **Error Rate**

## Model Management

### Loading Models

1. **Upload Models to Server**
```bash
# Copy models to droplet
scp -r ./models root@your-droplet-ip:/opt/sovereign-ai/

# Set permissions
ssh root@your-droplet-ip 'chown -R byos:byos /opt/sovereign-ai/models'
```

2. **Configure Model Cache**
```bash
# Update environment variables
MODEL_CACHE_DIR=/app/models
MAX_CONCURRENT_REQUESTS=8
GPU_MEMORY_FRACTION=0.8
```

### Recommended Models

- **LLaMA-2 7B/13B:** Good balance of performance and resource usage
- **Mistral 7B:** Excellent performance, lightweight
- **Code Llama:** For code generation tasks

## Backup and Recovery

### Database Backups

1. **Automated Backups**
```bash
# Backup script (runs daily via cron)
ssh root@your-droplet-ip 'crontab -l'
0 2 * * * docker-compose exec postgres pg_dump -U sovereign_user sovereign_production > /backup/backup_$(date +\%Y\%m\%d).sql
```

2. **Manual Backup**
```bash
# Create backup
ssh root@your-droplet-ip 'docker-compose exec postgres pg_dump -U sovereign_user sovereign_production > backup.sql'

# Restore backup
ssh root@your-droplet-ip 'docker-compose exec -T postgres psql -U sovereign_user sovereign_production < backup.sql'
```

### Full System Backup

```bash
# Backup entire application directory
ssh root@your-droplet-ip 'tar -czf /backup/sovereign-ai-backup-$(date +%Y%m%d).tar.gz /opt/sovereign-ai'
```

## Troubleshooting

### Common Issues

1. **GPU Not Detected**
```bash
# Check GPU status
nvidia-smi

# Check NVIDIA Docker
docker run --rm --gpus all nvidia/cuda:12.1-base nvidia-smi
```

2. **Out of Memory Errors**
```bash
# Reduce GPU memory fraction
GPU_MEMORY_FRACTION=0.6

# Reduce batch size
MODEL_BATCH_SIZE=2
```

3. **Slow API Response**
```bash
# Check resource usage
docker stats

# Scale up workers
docker-compose up -d --scale worker=4
```

### Log Analysis

```bash
# API logs
docker-compose logs -f api

# Worker logs
docker-compose logs -f worker

# Database logs
docker-compose logs -f postgres

# Nginx logs
docker-compose logs -f nginx
```

## Performance Optimization

### GPU Optimization

1. **Memory Management**
```bash
# Set appropriate GPU memory fraction
GPU_MEMORY_FRACTION=0.8

# Enable memory mapping
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
```

2. **Batch Processing**
```bash
# Optimize batch size based on GPU memory
MODEL_BATCH_SIZE=4
MAX_CONCURRENT_REQUESTS=8
```

### Database Optimization

1. **Connection Pooling**
```bash
SQLALCHEMY_ENGINE_OPTIONS=pool_size=20,max_overflow=30,pool_timeout=30,pool_recycle=3600
```

2. **Read Replicas** (for high traffic)
```bash
# Configure read replica in docker-compose
# Update DATABASE_URL with replica configuration
```

## Security

### Network Security

1. **Firewall Configuration**
```bash
# Configure UFW firewall
ssh root@your-droplet-ip 'ufw allow ssh'
ssh root@your-droplet-ip 'ufw allow 80'
ssh root@your-droplet-ip 'ufw allow 443'
ssh root@your-droplet-ip 'ufw enable'
```

2. **Fail2Ban Setup**
```bash
# Install fail2ban
ssh root@your-droplet-ip 'apt install fail2ban'

# Configure for nginx and ssh
ssh root@your-droplet-ip 'cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local'
```

### Application Security

1. **Environment Variable Security**
   - Use strong, unique secrets
   - Rotate keys regularly
   - Never commit secrets to git

2. **API Security**
   - Enable rate limiting
   - Use HTTPS everywhere
   - Implement proper authentication

## Scaling

### Horizontal Scaling

1. **Multiple Droplets**
   - Load balancer setup
   - Database clustering
   - Shared storage

2. **Kubernetes Deployment**
   - Digital Ocean Kubernetes (DOKS)
   - GPU node pools
   - Auto-scaling

### Vertical Scaling

1. **Upgrade Droplet Size**
```bash
# Resize droplet via Digital Ocean console
# Update resource limits in docker-compose.yml
```

2. **GPU Upgrades**
   - Multiple GPU configurations
   - GPU sharing strategies

## Cost Optimization

### Droplet Selection

- **Development:** Standard droplets, smaller sizes
- **Production:** GPU droplets for AI workloads
- **Staging:** Standard droplets, shared resources

### Resource Management

- **Auto-shutdown:** Schedule droplet shutdown for non-production
- **Spot Instances:** Use for batch processing
- **Monitoring:** Track resource usage to right-size

## Support

### Getting Help

1. **Digital Ocean Documentation**
   - [GPU Droplets](https://docs.digitalocean.com/products/droplets/how-to/gpu/)
   - [App Platform](https://docs.digitalocean.com/products/app-platform/)

2. **Community Support**
   - Digital Ocean Community
   - GitHub Issues
   - Stack Overflow

3. **Emergency Procedures**
   - Backup restoration
   - Service restart procedures
   - Emergency contacts

---

## Deployment Checklist

- [ ] Environment variables configured
- [ ] SSH keys set up
- [ ] SSL certificates installed
- [ ] Monitoring stack deployed
- [ ] Backup procedures tested
- [ ] Security measures implemented
- [ ] Performance optimized
- [ ] Documentation updated
- [ ] Team training completed
- [ ] Support procedures established

This deployment guide provides a comprehensive foundation for running the Sovereign AI SaaS Stack on Digital Ocean with full LLM capabilities.
