#!/usr/bin/env bash

set -Eeuo pipefail

BLUE="\033[1;34m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
NC="\033[0m"

log() { echo -e "${BLUE}[DO DEPLOY]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[DO DEPLOY]${NC} $1"; }
log_error() { echo -e "${RED}[DO DEPLOY]${NC} $1"; }
log_success() { echo -e "${GREEN}[DO DEPLOY]${NC} $1"; }

usage() {
    cat <<'EOF'
Usage: ./deploy-digital-ocean.sh [options]

Provision a hardened Digital Ocean Droplet and deploy the Sovereign AI SaaS stack.

Options:
  --droplet-name <name>        Name of the droplet (default: sovereign-ai-llm)
  --region <region>            Digital Ocean region slug (default: nyc3)
  --size <size>                Droplet size slug (default: g6-standard-4)
  --image <image>              Droplet image (default: docker-20-ubuntu-22-04)
  --ssh-key <fingerprint>      SSH key fingerprint registered in Digital Ocean (required)
  --env-file <path>            Path to production .env file (default: .env.production)
  --compose-file <path>        Docker Compose file to deploy (default: docker-compose.production.yml)
  --repo-url <url>             Git repository URL (default: https://github.com/reprewindai-dev/byosbackened.git)
  --branch <name>              Git branch to deploy (default: main)
  --app-host <https://host>    Public frontend URL (default: https://<ip>.nip.io)
  --api-host <https://host>    Public API URL (default: https://<ip>.nip.io)
  --firewall-name <name>       Firewall name (default: sovereign-ai-production-fw)
  --skip-firewall              Disable automatic firewall creation/attachment
  --skip-backups               Disable droplet backups
  --tags <tag1,tag2>           Comma separated Digital Ocean tags
  --doctl-bin <path>           doctl binary to use (default: doctl)
  --ssh-user <user>            SSH user for provisioning (default: root)
  -h, --help                   Show this help message
EOF
}

DROPLET_NAME="${DROPLET_NAME:-sovereign-ai-llm}"
REGION="${DIGITALOCEAN_REGION:-nyc3}"
SIZE="${DIGITALOCEAN_SIZE:-g6-standard-4}"
IMAGE="${DIGITALOCEAN_IMAGE:-docker-20-ubuntu-22-04}"
SSH_KEY_FINGERPRINT="${DO_SSH_KEY_FINGERPRINT:-}"
ENV_FILE=".env.production"
COMPOSE_FILE="docker-compose.production.yml"
REPO_URL="https://github.com/reprewindai-dev/byosbackened.git"
BRANCH="main"
APP_HOST=""
API_HOST=""
DOCTL_BIN="${DOCTL_BIN:-doctl}"
SSH_USER="root"
RAW_TAGS="sovereign-ai,production,llm-vps"
FIREWALL_NAME="sovereign-ai-production-fw"
ENABLE_FIREWALL=true
ENABLE_BACKUPS=true

while [[ $# -gt 0 ]]; do
    case "$1" in
        --droplet-name) DROPLET_NAME="$2"; shift 2 ;;
        --region) REGION="$2"; shift 2 ;;
        --size) SIZE="$2"; shift 2 ;;
        --image) IMAGE="$2"; shift 2 ;;
        --ssh-key) SSH_KEY_FINGERPRINT="$2"; shift 2 ;;
        --env-file) ENV_FILE="$2"; shift 2 ;;
        --compose-file) COMPOSE_FILE="$2"; shift 2 ;;
        --repo-url) REPO_URL="$2"; shift 2 ;;
        --branch) BRANCH="$2"; shift 2 ;;
        --app-host) APP_HOST="$2"; shift 2 ;;
        --api-host) API_HOST="$2"; shift 2 ;;
        --firewall-name) FIREWALL_NAME="$2"; shift 2 ;;
        --skip-firewall) ENABLE_FIREWALL=false; shift ;;
        --skip-backups) ENABLE_BACKUPS=false; shift ;;
        --tags) RAW_TAGS="$2"; shift 2 ;;
        --doctl-bin) DOCTL_BIN="$2"; shift 2 ;;
        --ssh-user) SSH_USER="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) log_error "Unknown argument: $1"; usage; exit 1 ;;
    esac
done

if [[ -z "$SSH_KEY_FINGERPRINT" ]]; then
    log_error "--ssh-key is required (or export DO_SSH_KEY_FINGERPRINT)."
    exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
    log_error "Env file $ENV_FILE not found."
    exit 1
fi

if [[ ! -f "$COMPOSE_FILE" ]]; then
    log_error "Compose file $COMPOSE_FILE not found."
    exit 1
fi

if grep -q "sk_live_your-stripe-secret-key-here" "$ENV_FILE"; then
    log_error "STRIPE_SECRET_KEY is still a placeholder. Update $ENV_FILE before deploying."
    exit 1
fi

if grep -q "pk_live_your-stripe-publishable-key-here" "$ENV_FILE"; then
    log_error "STRIPE_PUBLISHABLE_KEY is still a placeholder. Update $ENV_FILE before deploying."
    exit 1
fi

BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "workspace")
VERSION=$(grep -E '^VERSION=' "$ENV_FILE" | head -n1 | cut -d'=' -f2-)
VERSION=${VERSION:-1.0.0}

IFS=',' read -ra TAG_ARRAY <<< "$RAW_TAGS"
REMOTE_PATH="/opt/sovereign-ai"
SSH_TARGET="$SSH_USER@"

ensure_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        log_error "Missing dependency: $1"
        exit 1
    fi
}

ensure_command "$DOCTL_BIN"
ensure_command ssh
ensure_command scp

trap 'log_error "Deployment failed on line $LINENO"' ERR

SSH_FLAGS=(-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10)

get_droplet_id() {
    $DOCTL_BIN compute droplet list --format ID,Name --no-header \
        | awk -v name="$DROPLET_NAME" '$2 == name {print $1}'
}

create_droplet_if_needed() {
    DROPLET_ID=$(get_droplet_id || true)
    if [[ -z "$DROPLET_ID" ]]; then
        log "Creating droplet $DROPLET_NAME ($SIZE, $REGION)"
        create_args=(compute droplet create "$DROPLET_NAME" \
            --region "$REGION" \
            --size "$SIZE" \
            --image "$IMAGE" \
            --ssh-keys "$SSH_KEY_FINGERPRINT" \
            --enable-monitoring)
        if [[ "$ENABLE_BACKUPS" == true ]]; then
            create_args+=(--enable-backups)
        fi
        for tag in "${TAG_ARRAY[@]}"; do
            [[ -n "$tag" ]] && create_args+=(--tag-name "$tag")
        done
        "$DOCTL_BIN" "${create_args[@]}"
        "$DOCTL_BIN" compute droplet wait "$DROPLET_NAME"
        DROPLET_ID=$(get_droplet_id)
    else
        log "Droplet $DROPLET_NAME already exists (ID: $DROPLET_ID)."
    fi
    DROPLET_IP=$($DOCTL_BIN compute droplet get "$DROPLET_NAME" --format PublicIPv4 --no-header)
    if [[ -z "$DROPLET_IP" ]]; then
        log_error "Unable to resolve droplet IP."
        exit 1
    fi
    log "Droplet public IP: $DROPLET_IP"
}

wait_for_ssh() {
    log "Waiting for SSH to become available..."
    local attempt=1
    until ssh "${SSH_FLAGS[@]}" "$SSH_USER@$DROPLET_IP" "echo ok" >/dev/null 2>&1; do
        log_warn "SSH not ready yet (attempt ${attempt})."
        sleep 10
        ((attempt++))
    done
}

configure_firewall() {
    [[ "$ENABLE_FIREWALL" == true ]] || { log_warn "Skipping firewall configuration"; return; }
    log "Ensuring firewall $FIREWALL_NAME is configured"
    local firewall_id
    firewall_id=$($DOCTL_BIN compute firewall list --format ID,Name --no-header | awk -v name="$FIREWALL_NAME" '$2 == name {print $1}')
    if [[ -z "$firewall_id" ]]; then
        log "Creating firewall $FIREWALL_NAME"
        firewall_id=$($DOCTL_BIN compute firewall create \
            --name "$FIREWALL_NAME" \
            --inbound-rules "protocol:tcp,ports:22,address:0.0.0.0/0,address::/0" \
            --inbound-rules "protocol:tcp,ports:80,address:0.0.0.0/0,address::/0" \
            --inbound-rules "protocol:tcp,ports:443,address:0.0.0.0/0,address::/0" \
            --inbound-rules "protocol:tcp,ports:3000,address:0.0.0.0/0,address::/0" \
            --inbound-rules "protocol:tcp,ports:9090,address:0.0.0.0/0,address::/0" \
            --inbound-rules "protocol:tcp,ports:5601,address:0.0.0.0/0,address::/0" \
            --outbound-rules "protocol:tcp,ports:all,address:0.0.0.0/0,address::/0" \
            --outbound-rules "protocol:udp,ports:all,address:0.0.0.0/0,address::/0" \
            --droplet-ids "$DROPLET_ID" \
            --format ID --no-header)
    else
        log "Attaching droplet $DROPLET_ID to firewall $FIREWALL_NAME"
        $DOCTL_BIN compute firewall add-droplets "$firewall_id" --droplet-ids "$DROPLET_ID" >/dev/null
    fi
}

bootstrap_remote_host() {
    log "Bootstrapping remote host packages"
    ssh "${SSH_FLAGS[@]}" "$SSH_USER@$DROPLET_IP" REPO_URL="$REPO_URL" BRANCH="$BRANCH" 'bash -s' <<'EOF'
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get upgrade -y
apt-get install -y ca-certificates curl git ufw fail2ban software-properties-common
if ! command -v docker >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi
if ! docker compose version >/dev/null 2>&1 && ! command -v docker-compose >/dev/null 2>&1; then
    apt-get install -y docker-compose-plugin
fi
mkdir -p /opt/sovereign-ai
if [[ ! -d /opt/sovereign-ai/.git ]]; then
    git clone "$REPO_URL" /opt/sovereign-ai
fi
cd /opt/sovereign-ai
git fetch --all --tags
git checkout "$BRANCH"
git reset --hard "origin/$BRANCH"
mkdir -p data logs static models backup infra/docker/{nginx,postgres,redis,ssl} /opt/sovereign-ai/temp
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 3000/tcp
ufw allow 9090/tcp
ufw allow 5601/tcp
ufw --force enable
systemctl enable fail2ban
systemctl restart fail2ban
EOF
}

sync_payload() {
    log "Syncing environment and compose files"
    scp "${SSH_FLAGS[@]}" "$ENV_FILE" "$SSH_USER@$DROPLET_IP:$REMOTE_PATH/.env.production"
    scp "${SSH_FLAGS[@]}" "$ENV_FILE" "$SSH_USER@$DROPLET_IP:$REMOTE_PATH/.env"
    scp "${SSH_FLAGS[@]}" "$COMPOSE_FILE" "$SSH_USER@$DROPLET_IP:$REMOTE_PATH/docker-compose.yml"
}

configure_remote_env() {
    [[ -n "$APP_HOST" ]] || APP_HOST="https://$DROPLET_IP.nip.io"
    [[ -n "$API_HOST" ]] || API_HOST="https://$DROPLET_IP.nip.io"
    log "Configuring runtime environment URLs"
    ssh "${SSH_FLAGS[@]}" "$SSH_USER@$DROPLET_IP" APP_HOST="$APP_HOST" API_HOST="$API_HOST" BUILD_DATE="$BUILD_DATE" VCS_REF="$VCS_REF" VERSION="$VERSION" 'bash -s' <<'EOF'
set -Eeuo pipefail
PROJECT_ROOT="/opt/sovereign-ai"
cd "$PROJECT_ROOT"

update_kv() {
    local key="$1"
    local value="$2"
    local escaped=${value//&/\&}
    escaped=${escaped//|/\|}
    if grep -q "^${key}=" .env; then
        sed -i "s|^${key}=.*|${key}=${escaped}|" .env
    else
        echo "${key}=${value}" >> .env
    fi
}

update_kv "FRONTEND_URL" "$APP_HOST"
update_kv "API_URL" "$API_HOST"
update_kv "BUILD_DATE" "$BUILD_DATE"
update_kv "VCS_REF" "$VCS_REF"
update_kv "VERSION" "$VERSION"

if grep -q "sk_live_your-stripe-secret-key-here" .env; then
    echo "Stripe secret key is still placeholder" >&2
    exit 1
fi
if grep -q "pk_live_your-stripe-publishable-key-here" .env; then
    echo "Stripe publishable key is still placeholder" >&2
    exit 1
fi
EOF
}

deploy_stack() {
    log "Building and starting containers"
    ssh "${SSH_FLAGS[@]}" "$SSH_USER@$DROPLET_IP" BUILD_DATE="$BUILD_DATE" VCS_REF="$VCS_REF" VERSION="$VERSION" 'bash -s' <<'EOF'
set -Eeuo pipefail
PROJECT_ROOT="/opt/sovereign-ai"
cd "$PROJECT_ROOT"

if command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_BIN="docker-compose"
else
    COMPOSE_BIN="docker compose"
fi

$COMPOSE_BIN down --remove-orphans || true
$COMPOSE_BIN pull
$COMPOSE_BIN build --build-arg BUILD_DATE="$BUILD_DATE" --build-arg VCS_REF="$VCS_REF" --build-arg VERSION="$VERSION"
$COMPOSE_BIN up -d --remove-orphans
sleep 25
$COMPOSE_BIN exec -T api alembic upgrade head

cat >/etc/systemd/system/sovereign-ai.service <<'UNIT'
[Unit]
Description=Sovereign AI SaaS Stack
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/sovereign-ai
ExecStart=/usr/bin/docker compose --env-file /opt/sovereign-ai/.env up -d --remove-orphans
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0
User=root

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable sovereign-ai.service
systemctl restart sovereign-ai.service
EOF
}

print_summary() {
    log_success "Deployment complete"
    echo "---------------------------------------------"
    echo "Droplet:	$DROPLET_NAME ($DROPLET_IP)"
    echo "Frontend:	$APP_HOST"
    echo "API:	$API_HOST"
    echo "Grafana:	http://$DROPLET_IP:3000"
    echo "Prometheus:	http://$DROPLET_IP:9090"
    [[ "$ENABLE_FIREWALL" == true ]] && echo "Firewall:	$FIREWALL_NAME"
    echo "Version:	$VERSION ($VCS_REF @ $BUILD_DATE)"
    echo "---------------------------------------------"
}

log "🚀 Deploying Sovereign AI SaaS to Digital Ocean"
create_droplet_if_needed
wait_for_ssh
configure_firewall
bootstrap_remote_host
sync_payload
configure_remote_env
deploy_stack
print_summary
