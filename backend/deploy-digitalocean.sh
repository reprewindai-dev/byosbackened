#!/usr/bin/env bash
# ============================================================
# BYOS AI + Security Suite — Digital Ocean One-Command Deploy
# ============================================================
# Usage: bash deploy-digitalocean.sh [your-domain.com]
# Requirements: Ubuntu 22.04 LTS droplet, 4GB RAM minimum
# Recommended: DO droplet $24/mo (4 vCPU, 8GB RAM) or larger
# ============================================================
set -euo pipefail

DOMAIN="${1:-}"
APP_DIR="/opt/byos"
REPO_URL="${REPO_URL:-}"  # Set if deploying from git
COMPOSE_FILE="docker-compose.prod.yml"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${GREEN}[$(date +%H:%M:%S)] $*${NC}"; }
warn() { echo -e "${YELLOW}[WARN] $*${NC}"; }
err()  { echo -e "${RED}[ERR] $*${NC}"; exit 1; }

# ── Preflight ────────────────────────────────────────────────────────────────

if [[ $EUID -ne 0 ]]; then
  err "Run as root: sudo bash deploy-digitalocean.sh"
fi

log "BYOS AI + Security Suite — Digital Ocean Deploy"
echo -e "${BLUE}================================================${NC}"

# ── System packages ──────────────────────────────────────────────────────────

log "Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq \
  curl wget git unzip jq \
  ufw fail2ban \
  ca-certificates gnupg lsb-release

# ── Docker ───────────────────────────────────────────────────────────────────

if ! command -v docker &>/dev/null; then
  log "Installing Docker..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker
  systemctl start docker
else
  log "Docker already installed: $(docker --version)"
fi

if ! command -v docker-compose &>/dev/null && ! docker compose version &>/dev/null 2>&1; then
  log "Installing Docker Compose plugin..."
  apt-get install -y docker-compose-plugin
fi

# ── Firewall ─────────────────────────────────────────────────────────────────

log "Configuring UFW firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# ── Fail2ban ─────────────────────────────────────────────────────────────────

log "Configuring fail2ban..."
cat > /etc/fail2ban/jail.local <<'EOF'
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 5
backend  = systemd

[sshd]
enabled = true

[nginx-http-auth]
enabled = true
EOF
systemctl enable fail2ban
systemctl restart fail2ban

# ── App directory ────────────────────────────────────────────────────────────

log "Setting up application directory: $APP_DIR"
mkdir -p "$APP_DIR"

if [[ -n "$REPO_URL" ]]; then
  if [[ -d "$APP_DIR/.git" ]]; then
    cd "$APP_DIR" && git pull
  else
    git clone "$REPO_URL" "$APP_DIR"
  fi
else
  # Copy from current directory if running locally
  cp -r . "$APP_DIR/" 2>/dev/null || true
fi

cd "$APP_DIR"

# ── Environment setup ────────────────────────────────────────────────────────

if [[ ! -f "$APP_DIR/.env" ]]; then
  log "Generating .env from template..."
  if [[ -f "$APP_DIR/.env.example" ]]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  fi

  # Auto-generate secure secrets
  SECRET_KEY=$(openssl rand -hex 32)
  ENCRYPTION_KEY=$(openssl rand -hex 32)
  POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
  REDIS_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
  GRAFANA_PASSWORD=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 16)
  MINIO_SECRET=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)

  cat >> "$APP_DIR/.env" <<EOF

# === AUTO-GENERATED SECRETS ($(date)) ===
SECRET_KEY=${SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
REDIS_PASSWORD=${REDIS_PASSWORD}
GRAFANA_PASSWORD=${GRAFANA_PASSWORD}
S3_SECRET_ACCESS_KEY=${MINIO_SECRET}
EOF

  warn "⚠  .env generated. Edit $APP_DIR/.env to add Stripe keys, AI provider keys, etc."
  warn "   Required before going live: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, OPENAI_API_KEY (optional)"
else
  log ".env already exists, skipping generation."
fi

# ── SSL certificates ─────────────────────────────────────────────────────────

mkdir -p "$APP_DIR/infra/nginx/ssl/live"

if [[ -n "$DOMAIN" ]]; then
  log "Setting up Let's Encrypt SSL for: $DOMAIN"
  apt-get install -y certbot

  # Start nginx temporarily on port 80 for ACME challenge
  if ! docker ps | grep -q byos_nginx; then
    certbot certonly --standalone \
      --non-interactive --agree-tos \
      --email "admin@${DOMAIN}" \
      -d "$DOMAIN" \
      --pre-hook "docker compose -f $APP_DIR/$COMPOSE_FILE stop nginx 2>/dev/null || true" \
      --post-hook "docker compose -f $APP_DIR/$COMPOSE_FILE start nginx 2>/dev/null || true"
  fi

  # Copy certs for nginx
  cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$APP_DIR/infra/nginx/ssl/live/"
  cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$APP_DIR/infra/nginx/ssl/live/"

  # Auto-renew cron
  (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet && cp /etc/letsencrypt/live/${DOMAIN}/fullchain.pem ${APP_DIR}/infra/nginx/ssl/live/ && cp /etc/letsencrypt/live/${DOMAIN}/privkey.pem ${APP_DIR}/infra/nginx/ssl/live/ && docker compose -f ${APP_DIR}/${COMPOSE_FILE} restart nginx") | crontab -
  log "Let's Encrypt SSL configured with auto-renewal."
else
  warn "No domain provided — generating self-signed certificate for testing."
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$APP_DIR/infra/nginx/ssl/live/privkey.pem" \
    -out "$APP_DIR/infra/nginx/ssl/live/fullchain.pem" \
    -subj "/C=US/O=BYOS AI/CN=localhost" 2>/dev/null
fi

# ── Database migrations ───────────────────────────────────────────────────────

log "Starting database (postgres + redis)..."
docker compose -f "$APP_DIR/$COMPOSE_FILE" up -d postgres redis
sleep 10

log "Running database migrations..."
docker compose -f "$APP_DIR/$COMPOSE_FILE" run --rm api alembic upgrade head || \
  warn "Migration failed — check logs: docker logs byos_api"

# ── Deploy full stack ─────────────────────────────────────────────────────────

log "Deploying full stack..."
docker compose -f "$APP_DIR/$COMPOSE_FILE" up -d

# ── Post-deploy verification ─────────────────────────────────────────────────

log "Waiting for API to be healthy..."
for i in $(seq 1 20); do
  if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
    log "✅ API is healthy!"
    break
  fi
  if [[ $i -eq 20 ]]; then
    warn "API health check failed. Check: docker logs byos_api"
  fi
  sleep 3
done

# ── Systemd service for auto-restart on reboot ───────────────────────────────

log "Creating systemd service for auto-restart..."
cat > /etc/systemd/system/byos.service <<EOF
[Unit]
Description=BYOS AI + Security Suite
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${APP_DIR}
ExecStart=/usr/bin/docker compose -f ${COMPOSE_FILE} up -d
ExecStop=/usr/bin/docker compose -f ${COMPOSE_FILE} down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable byos

# ── Summary ──────────────────────────────────────────────────────────────────

SERVER_IP=$(curl -s http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address 2>/dev/null || hostname -I | awk '{print $1}')

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║      BYOS AI + Security Suite — DEPLOYED             ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BLUE}API Endpoint:${NC}     https://${DOMAIN:-$SERVER_IP}/api/v1"
echo -e "  ${BLUE}API Docs:${NC}         https://${DOMAIN:-$SERVER_IP}/api/v1/docs"
echo -e "  ${BLUE}Health Check:${NC}     https://${DOMAIN:-$SERVER_IP}/health"
echo -e "  ${BLUE}Grafana:${NC}          https://${DOMAIN:-$SERVER_IP}/grafana/"
echo -e "  ${BLUE}Grafana Login:${NC}    admin / (see .env GRAFANA_PASSWORD)"
echo ""
echo -e "  ${YELLOW}Next steps:${NC}"
echo -e "  1. Edit ${APP_DIR}/.env — add Stripe, AI provider keys"
echo -e "  2. Restart: docker compose -f ${APP_DIR}/${COMPOSE_FILE} restart"
echo -e "  3. View logs: docker compose -f ${APP_DIR}/${COMPOSE_FILE} logs -f api"
echo ""
echo -e "  ${YELLOW}Manage:${NC}"
echo -e "  Stop:    systemctl stop byos"
echo -e "  Start:   systemctl start byos"
echo -e "  Update:  cd ${APP_DIR} && git pull && docker compose -f ${COMPOSE_FILE} up -d --build"
echo ""
