#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# GoonVault — Server Setup Script for veklom.dev
# Run this ONCE on a fresh DigitalOcean Ubuntu 22.04 droplet.
# Usage: bash deploy-veklom.sh YOUR_GITHUB_REPO_URL
# Example: bash deploy-veklom.sh https://github.com/yourusername/WindSurf-Repo
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_URL="${1:-}"
APP_DIR="/opt/goonvault"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*"; exit 1; }

[[ $EUID -ne 0 ]] && error "Run as root: sudo bash deploy-veklom.sh ..."
[[ -z "$REPO_URL" ]] && error "Provide your GitHub repo URL as argument"

# ── 1. System packages ────────────────────────────────────────────────────────
info "Updating system..."
apt-get update -qq && apt-get upgrade -y -qq

info "Installing dependencies..."
apt-get install -y -qq \
    curl git ufw fail2ban \
    ca-certificates gnupg lsb-release

# ── 2. Docker ─────────────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    info "Installing Docker..."
    curl -fsSL https://get.docker.com | bash
    systemctl enable docker
    systemctl start docker
else
    info "Docker already installed: $(docker --version)"
fi

if ! docker compose version &>/dev/null; then
    info "Installing Docker Compose plugin..."
    apt-get install -y -qq docker-compose-plugin
fi

# ── 3. Firewall ───────────────────────────────────────────────────────────────
info "Configuring firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# ── 4. Clone repo ─────────────────────────────────────────────────────────────
info "Cloning repository to $APP_DIR..."
if [[ -d "$APP_DIR" ]]; then
    warn "Directory exists — pulling latest..."
    git -C "$APP_DIR" pull
else
    git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"

# ── 5. .env setup ─────────────────────────────────────────────────────────────
if [[ ! -f "$APP_DIR/.env" ]]; then
    cp "$APP_DIR/.env.veklom" "$APP_DIR/.env"
    warn "────────────────────────────────────────────────────────"
    warn "ACTION REQUIRED: Edit your .env file before continuing!"
    warn "Run: nano $APP_DIR/.env"
    warn "Fill in all CHANGE_ME values, then run this script again"
    warn "or run: cd $APP_DIR && docker compose -f docker-compose.veklom.yml up -d"
    warn "────────────────────────────────────────────────────────"
    exit 0
fi

# Check for unfilled placeholders
if grep -q "CHANGE_ME" "$APP_DIR/.env"; then
    error ".env still has CHANGE_ME placeholders. Edit it first: nano $APP_DIR/.env"
fi

# ── 6. Create required directories ───────────────────────────────────────────
info "Creating data directories..."
mkdir -p "$APP_DIR/data" "$APP_DIR/logs"
chmod 755 "$APP_DIR/data" "$APP_DIR/logs"

# ── 7. Build and launch ───────────────────────────────────────────────────────
info "Building and starting GoonVault..."
cd "$APP_DIR"
docker compose -f docker-compose.veklom.yml pull --quiet
docker compose -f docker-compose.veklom.yml up -d --build

# ── 8. Run DB migrations ──────────────────────────────────────────────────────
info "Waiting for API to be healthy..."
for i in {1..20}; do
    if docker exec goonvault-api curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        info "API is up!"
        break
    fi
    sleep 3
done

info "Running database migrations..."
docker exec goonvault-api python -m alembic upgrade head 2>/dev/null || \
    warn "Migrations skipped (may already be applied)"

# ── 9. Status ─────────────────────────────────────────────────────────────────
info "────────────────────────────────────────────────────────"
info "GoonVault is LIVE at https://veklom.dev"
info ""
info "Container status:"
docker compose -f docker-compose.veklom.yml ps
info ""
info "View logs: docker compose -f docker-compose.veklom.yml logs -f api"
info "────────────────────────────────────────────────────────"
