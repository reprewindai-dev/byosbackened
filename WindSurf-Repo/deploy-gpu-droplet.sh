#!/bin/bash

# Digital Ocean GPU Droplet Setup Script
# Optimized for LLM workloads with GPU support

set -e

echo "🚀 Setting up Digital Ocean GPU Droplet for LLM VPS..."

# Configuration
DROPLET_NAME="sovereign-ai-gpu"
REGION="nyc3"
SIZE="g6-standard-4"  # GPU optimized with NVIDIA A10G
IMAGE="docker-20-ubuntu-22-04"
SSH_KEY_FINGERPRINT="your-ssh-key-fingerprint"

# Create the droplet
echo "📦 Creating GPU Droplet..."
doctl compute droplet create $DROPLET_NAME \
    --region $REGION \
    --size $SIZE \
    --image $IMAGE \
    --ssh-keys $SSH_KEY_FINGERPRINT \
    --enable-monitoring \
    --tag-name sovereign-ai,gpu,llm-vps,production

# Wait for droplet to be ready
echo "⏳ Waiting for droplet to be ready..."
doctl compute droplet wait $DROPLET_NAME

# Get droplet IP
DROPLET_IP=$(doctl compute droplet get $DROPLET_NAME --format PublicIPv4 --no-header)
echo "🌐 Droplet IP: $DROPLET_IP"

# Wait for SSH to be available
echo "🔐 Waiting for SSH availability..."
while ! ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@$DROPLET_IP "echo 'SSH ready'" 2>/dev/null; do
    echo "Waiting for SSH..."
    sleep 10
done

# Setup droplet with GPU support
echo "⚙️ Setting up GPU droplet..."
ssh -o StrictHostKeyChecking=no root@$DROPLET_IP << 'EOF'
# Update system
apt update && apt upgrade -y

# Install NVIDIA drivers and CUDA
wget https://developer.download.nvidia.com/compute/cuda/12.1.1/local_installers/cuda_12.1.1_530.30.02_linux.run
sh cuda_12.1.1_530.30.02_linux.run --silent --toolkit

# Install Docker with NVIDIA support
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | tee /etc/apt/sources.list.d/nvidia-docker.list

apt update
apt install -y nvidia-docker2
systemctl restart docker

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install additional utilities
apt install -y git curl wget htop nvtop

# Create app directory
mkdir -p /opt/sovereign-ai
cd /opt/sovereign-ai

# Clone repository
git clone https://github.com/your-username/sovereign-ai-saas.git .

# Create necessary directories
mkdir -p data logs static models infra/docker/{nginx,postgres,redis,prometheus,grafana}

# Set permissions
chmod 755 /opt/sovereign-ai
chown -R root:root /opt/sovereign-ai

# Verify GPU installation
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.1-base-ubuntu22.04 nvidia-smi

EOF

# Copy environment files
echo "📋 Copying environment configuration..."
scp -o StrictHostKeyChecking=no .env.production root@$DROPLET_IP:/opt/sovereign-ai/.env
scp -o StrictHostKeyChecking=no docker-compose.llm-vps.yml root@$DROPLET_IP:/opt/sovereign-ai/docker-compose.yml

# Deploy application with GPU support
echo "🚀 Deploying LLM application with GPU support..."
ssh -o StrictHostKeyChecking=no root@$DROPLET_IP << 'EOF'
cd /opt/sovereign-ai

# Generate secure secrets if not set
if ! grep -q "your-super-secure" .env; then
    echo "✅ Environment already configured"
else
    echo "🔐 Generating secure secrets..."
    SECRET_KEY=$(openssl rand -base64 64)
    AI_CITIZENSHIP_SECRET=$(openssl rand -base64 64)
    POSTGRES_PASSWORD=$(openssl rand -base64 32)
    REDIS_PASSWORD=$(openssl rand -base64 32)
    GRAFANA_PASSWORD=$(openssl rand -base64 32)

    # Update .env file
    sed -i "s/your-super-secure-64-character-random-secret-key-here-change-this/$SECRET_KEY/g" .env
    sed -i "s/your-ai-citizenship-secret-key-here-change-this/$AI_CITIZENSHIP_SECRET/g" .env
    sed -i "s/your-secure-postgres-password-here/$POSTGRES_PASSWORD/g" .env
    sed -i "s/your-secure-redis-password-here/$REDIS_PASSWORD/g" .env
    sed -i "s/your-secure-grafana-password-here/$GRAFANA_PASSWORD/g" .env
    sed -i "s/your-domain.com/$(curl -s http://checkip.amazonaws.com).nip.io/g" .env
fi

# Add LLM-specific environment variables
cat >> .env << 'EOL'

# LLM Configuration
MODEL_CACHE_DIR=/app/models
MAX_CONCURRENT_REQUESTS=10
MODEL_MAX_LENGTH=4096
GPU_MEMORY_FRACTION=0.8
CUDA_VISIBLE_DEVICES=0

# Performance Tuning
OMP_NUM_THREADS=4
TOKENIZERS_PARALLELISM=false
EOL

# Build and start services with GPU support
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 60

# Check service status
docker-compose ps

# Run database migrations
docker-compose exec api alembic upgrade head

# Verify GPU access in containers
docker-compose exec api nvidia-smi

echo "✅ GPU deployment complete!"
EOF

echo "🎉 Sovereign AI LLM VPS deployed successfully!"
echo "🌐 Access your application at: http://$DROPLET_IP"
echo "📊 Monitoring at: http://$DROPLET_IP:3000 (Grafana)"
echo "🔍 Metrics at: http://$DROPLET_IP:9090 (Prometheus)"
echo ""
echo "🚀 GPU Status:"
echo "Check GPU utilization: ssh root@$DROPLET_IP 'nvidia-smi'"
echo "Check container GPU access: ssh root@$DROPLET_IP 'docker-compose exec api nvidia-smi'"
echo ""
echo "📝 Next steps:"
echo "1. Update your DNS to point to $DROPLET_IP"
echo "2. Configure SSL certificates"
echo "3. Set up backup and monitoring alerts"
echo "4. Update your API keys in the .env file"
echo "5. Load your LLM models to /opt/sovereign-ai/models"
