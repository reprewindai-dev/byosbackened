#!/bin/bash

# Digital Ocean Environment Setup Script
# Configures environment variables for different deployment targets

set -e

DEPLOYMENT_TYPE=${1:-"gpu"}  # gpu, standard, app-platform
DOMAIN=${2:-"auto"}

echo "🚀 Setting up environment for $DEPLOYMENT_TYPE deployment..."

# Source the environment setup
source setup-env.sh $DOMAIN

case $DEPLOYMENT_TYPE in
    "gpu")
        echo "🎮 Configuring for GPU Droplet deployment..."
        
        # GPU-specific configurations
        cat >> .env.production << EOF

# GPU Configuration
CUDA_VISIBLE_DEVICES=0
GPU_MEMORY_FRACTION=0.8
TORCH_CUDA_ARCH_LIST="7.5;8.0;8.6"
NVIDIA_VISIBLE_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Model Configuration
MODEL_CACHE_DIR=/app/models
MAX_CONCURRENT_REQUESTS=8
MODEL_BATCH_SIZE=4
MODEL_MAX_LENGTH=4096

# Performance Tuning
OMP_NUM_THREADS=8
TOKENIZERS_PARALLELISM=false
CUDA_LAUNCH_BLOCKING=0
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
EOF
        ;;
        
    "standard")
        echo "🖥️  Configuring for standard Droplet deployment..."
        
        # Standard CPU-only configurations
        cat >> .env.production << EOF

# CPU Configuration
MODEL_CACHE_DIR=/app/models
MAX_CONCURRENT_REQUESTS=4
MODEL_BATCH_SIZE=2
MODEL_MAX_LENGTH=2048

# Performance Tuning
OMP_NUM_THREADS=4
TOKENIZERS_PARALLELISM=false
CPU_WORKERS=4
EOF
        ;;
        
    "app-platform")
        echo "☁️  Configuring for App Platform deployment..."
        
        # App Platform specific configurations
        cat >> .env.production << EOF

# App Platform Configuration
PORT=\$PORT
INSTANCE_COUNT=1
INSTANCE_SIZE=professional-xs

# Resource Limits
MAX_MEMORY=4Gi
MAX_CPU=2
EOF
        ;;
        
    *)
        echo "❌ Invalid deployment type. Use: gpu, standard, or app-platform"
        exit 1
        ;;
esac

echo "✅ Environment configured for $DEPLOYMENT_TYPE deployment!"
echo "📋 Configuration file: .env.production"
