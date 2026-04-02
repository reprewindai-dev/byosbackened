# Deployment Guide

## Production Deployment Checklist

### 1. Pre-Deployment

- [ ] Generate `SECRET_KEY`: `openssl rand -hex 32`
- [ ] Configure domain name
- [ ] Obtain API keys (Hugging Face, SERP API)
- [ ] Set up DNS records (A record pointing to VPS IP)
- [ ] Configure firewall (ports 80, 443, SSH)

### 2. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 3. Application Deployment

```bash
# Clone repository
git clone <your-repo> /opt/byos-backend
cd /opt/byos-backend/backend

# Configure environment
cp .env.example .env
nano .env  # Edit with your values

# Update Caddyfile with your domain
nano infra/docker/Caddyfile

# Start services
cd infra/docker
docker compose up -d

# Run migrations
docker exec -it byos_api alembic upgrade head

# Create initial workspace (via API or SQL)
```

### 4. SSL/TLS Setup

Caddy automatically obtains Let's Encrypt certificates. Ensure:

- Domain DNS points to your server
- Ports 80 and 443 are open
- Email in Caddyfile is valid

### 5. Backup Configuration

```bash
# Create backup directory
sudo mkdir -p /backups
sudo chown $USER:$USER /backups

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * /opt/byos-backend/backend/infra/scripts/backup.sh

# Test backup
bash /opt/byos-backend/backend/infra/scripts/backup.sh
```

### 6. Monitoring

- Health endpoint: `https://your-domain.com/health`
- Set up uptime monitoring (UptimeRobot, Pingdom, etc.)
- Monitor logs: `docker logs -f byos_api`

### 7. Weekly Restore Test

```bash
# Add to crontab (weekly on Sunday at 3 AM)
0 3 * * 0 bash /opt/byos-backend/backend/infra/scripts/restore_test.sh
```

## Scaling

### Single Server → Multiple Servers

1. **Separate Database**
   - Move Postgres to dedicated server
   - Update `DATABASE_URL` in `.env`

2. **Separate Workers**
   - Deploy worker containers on separate servers
   - Same Redis broker, different hosts

3. **Load Balancer**
   - Multiple API instances behind load balancer
   - Update Caddyfile to proxy to multiple backends

### Kubernetes (Advanced)

When ready for K8s:
- Convert Docker Compose to Kubernetes manifests
- Use Helm charts for easier management
- Same containers, different orchestration

## Troubleshooting

### Database Connection Issues

```bash
# Check Postgres logs
docker logs byos_postgres

# Test connection
docker exec -it byos_postgres psql -U postgres -d byos_ai
```

### Worker Not Processing Jobs

```bash
# Check worker logs
docker logs byos_worker

# Check Redis
docker exec -it byos_redis redis-cli ping
```

### S3/MinIO Issues

```bash
# Check MinIO logs
docker logs byos_minio

# Access MinIO console
# http://your-server:9001 (minioadmin/minioadmin)
```

## Security Hardening

1. **Change default passwords**
   - Postgres: Set strong password
   - MinIO: Change root credentials
   - Redis: Consider password protection

2. **Firewall**
   - Only expose ports 80, 443, SSH
   - Block direct access to Postgres, Redis, MinIO

3. **Secrets Management**
   - Use Docker secrets or external secret manager
   - Never commit `.env` files

4. **Regular Updates**
   - Update Docker images regularly
   - Monitor security advisories

## Backup Verification

Test your backups monthly:

```bash
# Manual restore test
bash infra/scripts/restore_test.sh

# Verify backup age
ls -lh /backups/

# Test backup download (if stored remotely)
```

---

**Remember**: This backend is designed to be portable. You can move it to any VPS/provider in hours, not weeks.
