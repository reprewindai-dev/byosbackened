"""
Seked Production Deployment Pipeline
===================================

Complete production deployment pipeline for Seked infrastructure-grade AI governance.
Includes containerization, orchestration, CI/CD, monitoring, and scaling configuration.

Deployment Architecture:
- Kubernetes-based microservices
- Istio service mesh with mTLS
- Cloud-native storage and networking
- Automated scaling and self-healing
- Comprehensive monitoring and alerting
"""

import os
import yaml
import json
from typing import Dict, List, Any
from pathlib import Path


class SekedDeploymentPipeline:
    """Complete deployment pipeline for Seked production."""

    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.k8s_dir = self.root_dir / "k8s"
        self.docker_dir = self.root_dir / "docker"
        self.ci_cd_dir = self.root_dir / "ci-cd"

        # Create directory structure
        self._create_directory_structure()

    def _create_directory_structure(self):
        """Create deployment directory structure."""
        directories = [
            self.k8s_dir / "base",
            self.k8s_dir / "overlays" / "dev",
            self.k8s_dir / "overlays" / "staging",
            self.k8s_dir / "overlays" / "prod",
            self.docker_dir,
            self.ci_cd_dir / "github-actions",
            self.ci_cd_dir / "argocd",
            self.root_dir / "monitoring",
            self.root_dir / "infrastructure"
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


# Environment Variables Configuration
ENVIRONMENT_VARIABLES = """
# Seked Production Environment Variables
# Copy to .env.prod and configure for production deployment

# Application Configuration
APP_NAME=Seked
APP_VERSION=1.0.0
DEBUG=false
API_PREFIX=/api/v1
DATA_DIR=/app/data

# Database Configuration
DATABASE_URL=postgresql://seked_user:secure_password@seked-db-prod.cluster.example.com:5432/seked_prod
REDIS_URL=redis://seked-redis-prod.cluster.example.com:6379/0
REDIS_PASSWORD=secure_redis_password

# Security Configuration
SECRET_KEY=your-256-bit-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
ENCRYPTION_KEY=your-32-byte-encryption-key-here

# Stripe Billing Configuration
STRIPE_SECRET_KEY=sk_live_your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_live_your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# AI Provider Configuration
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
GOOGLE_AI_API_KEY=your-google-ai-key

# Blockchain Configuration
ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/your_infura_project_id
POLYGON_RPC_URL=https://polygon-mainnet.infura.io/v3/your_infura_project_id
BITCOIN_RPC_URL=http://bitcoin-node.example.com:8332
ETHEREUM_PRIVATE_KEY=your_ethereum_private_key
POLYGON_PRIVATE_KEY=your_polygon_private_key
BITCOIN_RPC_USER=seked_btc_user
BITCOIN_RPC_PASS=secure_bitcoin_password

# Istio Service Mesh Configuration
ISTIO_NAMESPACE=istio-system
SEKED_NAMESPACE=seked
TENANT_NAMESPACE=seked-tenants
ISTIO_INGRESS_IP=your_istio_ingress_ip

# External Services
EMAIL_SMTP_HOST=smtp.sendgrid.net
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=apikey
EMAIL_SMTP_PASS=your_sendgrid_api_key
CRM_API_KEY=your_crm_api_key
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/slack/webhook

# Monitoring and Logging
DATADOG_API_KEY=your_datadog_api_key
NEW_RELIC_LICENSE_KEY=your_new_relic_key
LOG_LEVEL=INFO
LOG_FORMAT=json

# Feature Flags
ENABLE_CONSENSUS=true
ENABLE_CITIZENNET=true
ENABLE_BLOCKCHAIN_ANCHORING=true
ENABLE_ADVANCED_COMPLIANCE=true

# Scaling Configuration
MAX_CITIZENS_PER_TENANT=10000
API_RATE_LIMIT_PER_MINUTE=10000
AUDIT_RETENTION_DAYS=2555

# Backup Configuration
BACKUP_SCHEDULE=0 2 * * *  # Daily at 2 AM UTC
BACKUP_RETENTION_DAYS=30
BACKUP_ENCRYPTION_KEY=your_backup_encryption_key
"""


# Docker Configuration
DOCKER_COMPOSE_PROD = """
version: '3.8'

services:
  seked-api:
    build:
      context: ..
      dockerfile: docker/Dockerfile.api
    environment:
      - DATABASE_URL=postgresql://seked:password@db:5432/seked
      - REDIS_URL=redis://redis:6379
    ports:
      - "8080:8080"
    depends_on:
      - db
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  seked-worker:
    build:
      context: ..
      dockerfile: docker/Dockerfile.worker
    environment:
      - DATABASE_URL=postgresql://seked:password@db:5432/seked
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    deploy:
      replicas: 3

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: seked
      POSTGRES_USER: seked
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U seked"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"

volumes:
  postgres_data:
  redis_data:
  grafana_data:
"""


# Kubernetes Base Manifests
K8S_BASE_CONFIGMAP = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: seked-config
  namespace: seked
data:
  APP_NAME: "Seked"
  APP_VERSION: "1.0.0"
  DEBUG: "false"
  API_PREFIX: "/api/v1"
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "json"
  ENABLE_CONSENSUS: "true"
  ENABLE_CITIZENNET: "true"
  ENABLE_BLOCKCHAIN_ANCHORING: "true"
  ENABLE_ADVANCED_COMPLIANCE: "true"
  MAX_CITIZENS_PER_TENANT: "10000"
  API_RATE_LIMIT_PER_MINUTE: "10000"
  AUDIT_RETENTION_DAYS: "2555"
"""

K8S_BASE_SECRET = """
apiVersion: v1
kind: Secret
metadata:
  name: seked-secrets
  namespace: seked
type: Opaque
stringData:
  SECRET_KEY: "your-256-bit-secret-key-here"
  JWT_SECRET_KEY: "your-jwt-secret-key-here"
  ENCRYPTION_KEY: "your-32-byte-encryption-key-here"
  STRIPE_SECRET_KEY: "sk_live_your_stripe_secret_key"
  STRIPE_WEBHOOK_SECRET: "whsec_your_webhook_secret"
  OPENAI_API_KEY: "sk-your-openai-key"
  ETHEREUM_PRIVATE_KEY: "your_ethereum_private_key"
  EMAIL_SMTP_PASS: "your_sendgrid_api_key"
  DATADOG_API_KEY: "your_datadog_api_key"
"""

K8S_BASE_DEPLOYMENT = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: seked-api-gateway
  namespace: seked
  labels:
    app.kubernetes.io/name: seked-api-gateway
    app.kubernetes.io/part-of: seked
spec:
  replicas: 3
  selector:
    matchLabels:
      app.kubernetes.io/name: seked-api-gateway
  template:
    metadata:
      labels:
        app.kubernetes.io/name: seked-api-gateway
        app.kubernetes.io/part-of: seked
    spec:
      serviceAccountName: seked-api-gateway
      containers:
      - name: api-gateway
        image: seked/api-gateway:latest
        ports:
        - containerPort: 8080
          name: http
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: seked-db-secret
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: seked-redis-secret
              key: redis-url
        envFrom:
        - configMapRef:
            name: seked-config
        - secretRef:
            name: seked-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
        securityContext:
          allowPrivilegeEscalation: false
          runAsNonRoot: true
          runAsUser: 1000
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
"""

K8S_BASE_SERVICE = """
apiVersion: v1
kind: Service
metadata:
  name: seked-api-gateway
  namespace: seked
  labels:
    app.kubernetes.io/name: seked-api-gateway
    app.kubernetes.io/part-of: seked
spec:
  selector:
    app.kubernetes.io/name: seked-api-gateway
  ports:
  - name: http
    port: 8080
    targetPort: 8080
    protocol: TCP
  type: ClusterIP
"""

K8S_BASE_HPA = """
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: seked-api-gateway-hpa
  namespace: seked
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: seked-api-gateway
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
"""

K8S_BASE_PDB = """
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: seked-api-gateway-pdb
  namespace: seked
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: seked-api-gateway
"""

K8S_BASE_SERVICEACCOUNT = """
apiVersion: v1
kind: ServiceAccount
metadata:
  name: seked-api-gateway
  namespace: seked
  labels:
    app.kubernetes.io/part-of: seked
"""

# Production Overlay
K8S_PROD_OVERLAY = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: seked-api-gateway
spec:
  replicas: 10  # Higher replicas for production
  template:
    spec:
      containers:
      - name: api-gateway
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        env:
        - name: LOG_LEVEL
          value: "WARNING"  # Less verbose logging in prod
"""

# Ingress Configuration
K8S_INGRESS = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: seked-ingress
  namespace: seked
  annotations:
    kubernetes.io/ingress.class: "nginx"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
spec:
  tls:
  - hosts:
    - api.seked.ai
    - admin.seked.ai
    secretName: seked-tls
  rules:
  - host: api.seked.ai
    http:
      paths:
      - path: /api/v1
        pathType: Prefix
        backend:
          service:
            name: seked-api-gateway
            port:
              number: 8080
  - host: admin.seked.ai
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: seked-admin-dashboard
            port:
              number: 3000
"""

# Certificate Manager
K8S_CERT_MANAGER = """
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: security@seked.ai
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
"""

# Network Policies
K8S_NETWORK_POLICY = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: seked-network-policy
  namespace: seked
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: istio-system
    - namespaceSelector:
        matchLabels:
          name: seked-tenants
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
  - to: []
    ports:
    - protocol: TCP
      port: 443  # Allow HTTPS outbound
"""

# Monitoring Configuration
PROMETHEUS_CONFIG = """
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
  - static_configs:
    - targets:
      - alertmanager:9093

scrape_configs:
  - job_name: 'seked-api-gateway'
    static_configs:
    - targets: ['seked-api-gateway:8080']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'seked-policy-engine'
    static_configs:
    - targets: ['seked-policy-engine:8080']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'seked-consensus-engine'
    static_configs:
    - targets: ['seked-consensus-engine:8080']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
    - role: pod
    relabel_configs:
    - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
      action: keep
      regex: true
    - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
      action: replace
      target_label: __metrics_path__
      regex: (.+)
    - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
      action: replace
      regex: ([^:]+)(?::\\d+)?;(\\d+)
      replacement: $1:$2
      target_label: __address__
"""

ALERT_RULES = """
groups:
- name: seked_alerts
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value }}%"

  - alert: ConsensusFailure
    expr: seked_consensus_decisions_total{result="failed"} > 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Consensus failure detected"
      description: "Consensus decisions are failing"

  - alert: CertificateExpiry
    expr: seked_certificate_expiry_days < 30
    for: 1h
    labels:
      severity: warning
    annotations:
      summary: "Certificate expiring soon"
      description: "Certificate expires in {{ $value }} days"

  - alert: HighLatency
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2.0
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High request latency"
      description: "95th percentile latency is {{ $value }}s"
"""

# CI/CD Configuration
GITHUB_ACTIONS_WORKFLOW = """
name: Seked CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Run tests
      run: |
        pytest tests/ -v --cov=core --cov-report=xml --cov-report=html
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
        REDIS_URL: redis://localhost:6379/0
        TESTING: true

    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2

    - name: Log in to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Build and push API image
      uses: docker/build-push-action@v4
      with:
        context: .
        file: docker/Dockerfile.api
        push: true
        tags: ghcr.io/${{ github.repository }}/api:latest
        cache-from: type=gha
        cache-to: type=gha,mode=max

    - name: Build and push Worker image
      uses: docker/build-push-action@v4
      with:
        context: .
        file: docker/Dockerfile.worker
        push: true
        tags: ghcr.io/${{ github.repository }}/worker:latest

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: staging

    steps:
    - name: Deploy to staging
      run: |
        echo "Deploying to staging environment"
        # ArgoCD sync or kubectl apply commands would go here

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    environment: production

    steps:
    - name: Deploy to production
      run: |
        echo "Deploying to production environment"
        # ArgoCD sync with production overlay
"""

# ArgoCD Application
ARGOCD_APPLICATION = """
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: seked
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/seked
    targetRevision: HEAD
    path: k8s/overlays/prod
  destination:
    server: https://kubernetes.default.svc
    namespace: seked
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
    - PrunePropagationPolicy=foreground
    - PruneLast=true
  revisionHistoryLimit: 10
"""

# Database Migration Scripts
DATABASE_MIGRATIONS = """
-- Seked Database Migrations
-- Run these in order during deployment

-- 001_initial_schema.sql
CREATE TABLE IF NOT EXISTS citizens (
    citizen_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    trust_tier TEXT NOT NULL,
    jurisdiction TEXT NOT NULL,
    capabilities JSONB NOT NULL DEFAULT '[]',
    certificate TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    stream_type TEXT NOT NULL,
    stream_id TEXT NOT NULL,
    event_data JSONB NOT NULL,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    prev_hash TEXT,
    entry_hash TEXT NOT NULL,
    sequence_number BIGINT NOT NULL,
    compliance_tags JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS policy_profiles (
    profile_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    rules JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 002_billing_schema.sql
CREATE TABLE IF NOT EXISTS customer_accounts (
    customer_id TEXT PRIMARY KEY,
    stripe_customer_id TEXT UNIQUE NOT NULL,
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    company_name TEXT,
    billing_address JSONB,
    payment_method_id TEXT,
    subscription_status TEXT NOT NULL DEFAULT 'inactive',
    current_period_end TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS citizen_subscriptions (
    subscription_id TEXT PRIMARY KEY,
    citizen_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    tier_id TEXT NOT NULL,
    stripe_subscription_id TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    current_period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    current_period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    addons JSONB DEFAULT '[]',
    auto_renew BOOLEAN DEFAULT TRUE,
    cancel_at_period_end BOOLEAN DEFAULT FALSE
);

-- 003_consensus_schema.sql
CREATE TABLE IF NOT EXISTS consensus_decisions (
    decision_id TEXT PRIMARY KEY,
    decision_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    proposed_action TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    proposed_by TEXT NOT NULL,
    proposed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    consensus_reached BOOLEAN DEFAULT FALSE,
    decision_result TEXT,
    ledger_reference TEXT,
    signatures JSONB DEFAULT '[]'
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_audit_events_stream ON audit_events(stream_type, stream_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events(recorded_at);
CREATE INDEX IF NOT EXISTS idx_citizens_tenant ON citizens(tenant_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_customer ON citizen_subscriptions(customer_id);
"""

# Health Check Scripts
HEALTH_CHECK_SCRIPT = """
#!/bin/bash
# Seked Production Health Check Script

echo "🔍 Seked Production Health Check"
echo "================================="

# Check Kubernetes cluster
echo "📊 Kubernetes Status:"
kubectl cluster-info
echo ""

# Check Seked namespace
echo "🏗️  Seked Namespace Status:"
kubectl get pods -n seked
echo ""

# Check Istio status
echo "🔐 Istio Status:"
kubectl get pods -n istio-system
echo ""

# API Health Check
echo "🌐 API Gateway Health:"
curl -f http://seked-api-gateway.seked.svc.cluster.local:8080/health || echo "❌ API unhealthy"
echo ""

# Database connectivity
echo "🗄️  Database Status:"
kubectl exec -n seked deployment/seked-api-gateway -- python -c "
import os
from core.config import get_settings
from sqlalchemy import create_engine, text

settings = get_settings()
engine = create_engine(settings.DATABASE_URL)
try:
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print('✅ Database connected')
except Exception as e:
    print(f'❌ Database error: {e}')
"
echo ""

# Redis connectivity
echo "⚡ Redis Status:"
kubectl exec -n seked deployment/seked-api-gateway -- python -c "
import redis
import os

redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
try:
    r = redis.from_url(redis_url)
    r.ping()
    print('✅ Redis connected')
except Exception as e:
    print(f'❌ Redis error: {e}')
"
echo ""

# Consensus health
echo "⚖️  Consensus Status:"
kubectl logs -n seked -l app=seked-consensus-engine --tail=10
echo ""

echo "✅ Health check complete"
"""

# Backup Scripts
BACKUP_SCRIPT = """
#!/bin/bash
# Seked Production Backup Script

BACKUP_DIR="/backups/seked"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="seked_backup_${TIMESTAMP}"

echo "💾 Creating Seked backup: ${BACKUP_NAME}"

# Create backup directory
mkdir -p ${BACKUP_DIR}/${BACKUP_NAME}

# Database backup
echo "📊 Backing up database..."
kubectl exec -n seked deployment/seked-api-gateway -- bash -c "
pg_dump -h seked-db-prod -U seked -d seked_prod > /tmp/seked_db.sql
"

kubectl cp seked/seked-api-gateway:/tmp/seked_db.sql ${BACKUP_DIR}/${BACKUP_NAME}/database.sql

# Configuration backup
echo "⚙️  Backing up configuration..."
kubectl get configmaps -n seked -o yaml > ${BACKUP_DIR}/${BACKUP_NAME}/configmaps.yaml
kubectl get secrets -n seked -o yaml > ${BACKUP_DIR}/${BACKUP_NAME}/secrets.yaml

# Audit data backup (Merkle roots and metadata)
echo "📋 Backing up audit metadata..."
kubectl exec -n seked deployment/seked-audit -- bash -c "
sqlite3 /app/data/audit_fabric.db .dump > /tmp/audit_dump.sql
"

kubectl cp seked/seked-audit:/tmp/audit_dump.sql ${BACKUP_DIR}/${BACKUP_NAME}/audit_metadata.sql

# Compress backup
echo "🗜️  Compressing backup..."
cd ${BACKUP_DIR}
tar -czf ${BACKUP_NAME}.tar.gz ${BACKUP_NAME}
rm -rf ${BACKUP_NAME}

# Encrypt backup (if encryption key provided)
if [ ! -z "$BACKUP_ENCRYPTION_KEY" ]; then
    echo "🔐 Encrypting backup..."
    openssl enc -aes-256-cbc -salt -in ${BACKUP_NAME}.tar.gz -out ${BACKUP_NAME}.enc -k $BACKUP_ENCRYPTION_KEY
    rm ${BACKUP_NAME}.tar.gz
fi

# Upload to cloud storage (example with AWS S3)
if [ ! -z "$AWS_ACCESS_KEY_ID" ]; then
    echo "☁️  Uploading to S3..."
    aws s3 cp ${BACKUP_DIR}/${BACKUP_NAME}.* s3://seked-backups/ --recursive
fi

echo "✅ Backup complete: ${BACKUP_NAME}"
"""

# Rollback Scripts
ROLLBACK_SCRIPT = """
#!/bin/bash
# Seked Production Rollback Script

ROLLBACK_VERSION=$1
if [ -z "$ROLLBACK_VERSION" ]; then
    echo "❌ Usage: $0 <version-tag>"
    exit 1
fi

echo "🔄 Rolling back Seked to version: ${ROLLBACK_VERSION}"

# Scale down current deployment
echo "⬇️  Scaling down current deployment..."
kubectl scale deployment seked-api-gateway -n seked --replicas=0
kubectl scale deployment seked-worker -n seked --replicas=0

# Wait for pods to terminate
echo "⏳ Waiting for pods to terminate..."
kubectl wait --for=delete pod -l app.kubernetes.io/part-of=seked -n seked --timeout=300s

# Update deployment images
echo "📦 Updating to rollback version..."
kubectl set image deployment/seked-api-gateway api-gateway=seked/api-gateway:${ROLLBACK_VERSION} -n seked
kubectl set image deployment/seked-worker worker=seked/worker:${ROLLBACK_VERSION} -n seked

# Scale back up
echo "⬆️  Scaling back up..."
kubectl scale deployment seked-api-gateway -n seked --replicas=3
kubectl scale deployment seked-worker -n seked --replicas=3

# Wait for rollout
echo "⏳ Waiting for rollout..."
kubectl rollout status deployment/seked-api-gateway -n seked --timeout=600s
kubectl rollout status deployment/seked-worker -n seked --timeout=600s

# Run health checks
echo "🔍 Running health checks..."
./scripts/health-check.sh

echo "✅ Rollback complete to version: ${ROLLBACK_VERSION}"
"""


def create_deployment_files():
    """Create all deployment configuration files."""

    # Create base Kubernetes manifests
    base_dir = Path("k8s/base")
    base_dir.mkdir(parents=True, exist_ok=True)

    with open(base_dir / "configmap.yaml", "w") as f:
        f.write(K8S_BASE_CONFIGMAP)

    with open(base_dir / "secret.yaml", "w") as f:
        f.write(K8S_BASE_SECRET)

    with open(base_dir / "deployment.yaml", "w") as f:
        f.write(K8S_BASE_DEPLOYMENT)

    with open(base_dir / "service.yaml", "w") as f:
        f.write(K8S_BASE_SERVICE)

    with open(base_dir / "hpa.yaml", "w") as f:
        f.write(K8S_BASE_HPA)

    with open(base_dir / "pdb.yaml", "w") as f:
        f.write(K8S_BASE_PDB)

    with open(base_dir / "serviceaccount.yaml", "w") as f:
        f.write(K8S_BASE_SERVICEACCOUNT)

    # Create production overlay
    prod_dir = Path("k8s/overlays/prod")
    prod_dir.mkdir(parents=True, exist_ok=True)

    with open(prod_dir / "deployment-patch.yaml", "w") as f:
        f.write(K8S_PROD_OVERLAY)

    with open(prod_dir / "ingress.yaml", "w") as f:
        f.write(K8S_INGRESS)

    with open(prod_dir / "cert-manager.yaml", "w") as f:
        f.write(K8S_CERT_MANAGER)

    with open(prod_dir / "network-policy.yaml", "w") as f:
        f.write(K8S_NETWORK_POLICY)

    # Create Docker files
    docker_dir = Path("docker")
    docker_dir.mkdir(exist_ok=True)

    with open(docker_dir / "docker-compose.prod.yml", "w") as f:
        f.write(DOCKER_COMPOSE_PROD)

    # Create monitoring configuration
    monitoring_dir = Path("monitoring")
    monitoring_dir.mkdir(exist_ok=True)

    with open(monitoring_dir / "prometheus.yml", "w") as f:
        f.write(PROMETHEUS_CONFIG)

    with open(monitoring_dir / "alert_rules.yml", "w") as f:
        f.write(ALERT_RULES)

    # Create CI/CD configuration
    ci_cd_dir = Path("ci-cd/github-actions")
    ci_cd_dir.mkdir(parents=True, exist_ok=True)

    with open(ci_cd_dir / "ci-cd-pipeline.yml", "w") as f:
        f.write(GITHUB_ACTIONS_WORKFLOW)

    argocd_dir = Path("ci-cd/argocd")
    argocd_dir.mkdir(parents=True, exist_ok=True)

    with open(argocd_dir / "application.yaml", "w") as f:
        f.write(ARGOCD_APPLICATION)

    # Create infrastructure scripts
    scripts_dir = Path("scripts")
    scripts_dir.mkdir(exist_ok=True)

    with open(scripts_dir / "health-check.sh", "w") as f:
        f.write(HEALTH_CHECK_SCRIPT)

    with open(scripts_dir / "backup.sh", "w") as f:
        f.write(BACKUP_SCRIPT)

    with open(scripts_dir / "rollback.sh", "w") as f:
        f.write(ROLLBACK_SCRIPT)

    # Create database migrations
    migrations_dir = Path("migrations")
    migrations_dir.mkdir(exist_ok=True)

    with open(migrations_dir / "001_initial_schema.sql", "w") as f:
        f.write(DATABASE_MIGRATIONS.split("-- 002_billing_schema.sql")[0])

    with open(migrations_dir / "002_billing_schema.sql", "w") as f:
        f.write("-- 002_billing_schema.sql" + DATABASE_MIGRATIONS.split("-- 002_billing_schema.sql")[1].split("-- 003_consensus_schema.sql")[0])

    with open(migrations_dir / "003_consensus_schema.sql", "w") as f:
        f.write("-- 003_consensus_schema.sql" + DATABASE_MIGRATIONS.split("-- 003_consensus_schema.sql")[1])

    # Create environment variables template
    with open(".env.prod.template", "w") as f:
        f.write(ENVIRONMENT_VARIABLES)

    print("✅ Production deployment files created successfully!")


if __name__ == "__main__":
    create_deployment_files()
