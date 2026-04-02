#!/bin/bash

# Monitoring and Logging Setup Script
# Configures comprehensive monitoring for Digital Ocean deployment

set -e

echo "📊 Setting up monitoring and logging infrastructure..."

# Create monitoring directories
mkdir -p infra/docker/{grafana,prometheus,elasticsearch,logstash,kibana}
mkdir -p logs/monitoring

# Create Grafana provisioning
cat > infra/docker/grafana/provisioning/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    editable: true
EOF

# Create Grafana dashboards provisioning
cat > infra/docker/grafana/provisioning/dashboards/dashboard.yml << EOF
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
EOF

# Create Loki configuration
cat > infra/docker/loki/loki.yml << EOF
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
    final_sleep: 0s
  chunk_idle_period: 1h
  max_chunk_age: 1h
  chunk_target_size: 1048576
  chunk_retain_period: 30s

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/boltdb-shipper-active
    cache_location: /loki/boltdb-shipper-cache
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h

chunk_store_config:
  max_look_back_period: 0s

table_manager:
  retention_deletes_enabled: false
  retention_period: 0s
EOF

# Create Promtail configuration
cat > infra/docker/promtail/promtail.yml << EOF
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
- job_name: containers
  static_configs:
  - targets:
      - localhost
    labels:
      job: containerlogs
      __path__: /var/lib/docker/containers/*/*log

  pipeline_stages:
  - json:
      expressions:
        output: log
        stream: stream
        attrs:
  - json:
      expressions:
        tag:
      source: attrs
  - regex:
      expression: (?P<container_name>(?:[^|]*))\|
      source: tag
  - timestamp:
      format: RFC3339Nano
      source: time
  - labels:
      stream:
      container_name:
  - output:
      source: output

- job_name: system
  static_configs:
  - targets:
      - localhost
    labels:
      job: varlogs
      __path__: /var/log/*log
EOF

# Create docker-compose.monitoring.yml
cat > docker-compose.monitoring.yml << EOF
version: '3.8'

services:
  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    container_name: sovereign-prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'
    volumes:
      - ./infra/docker/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - sovereign-network
    restart: unless-stopped

  # Grafana
  grafana:
    image: grafana/grafana:latest
    container_name: sovereign-grafana
    environment:
      GF_SECURITY_ADMIN_PASSWORD: \${GRAFANA_PASSWORD}
      GF_USERS_ALLOW_SIGN_UP: false
      GF_INSTALL_PLUGINS: grafana-piechart-panel,grafana-worldmap-panel
    volumes:
      - grafana_data:/var/lib/grafana
      - ./infra/docker/grafana/provisioning:/etc/grafana/provisioning
    ports:
      - "3000:3000"
    networks:
      - sovereign-network
    depends_on:
      - prometheus
    restart: unless-stopped

  # Loki
  loki:
    image: grafana/loki:latest
    container_name: sovereign-loki
    command: -config.file=/etc/loki/local-config.yaml
    volumes:
      - ./infra/docker/loki/loki.yml:/etc/loki/local-config.yaml
      - loki_data:/loki
    ports:
      - "3100:3100"
    networks:
      - sovereign-network
    restart: unless-stopped

  # Promtail
  promtail:
    image: grafana/promtail:latest
    container_name: sovereign-promtail
    volumes:
      - ./infra/docker/promtail/promtail.yml:/etc/promtail/config.yml
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/log:/var/log:ro
    command: -config.file=/etc/promtail/config.yml
    networks:
      - sovereign-network
    depends_on:
      - loki
    restart: unless-stopped

  # Node Exporter
  node-exporter:
    image: prom/node-exporter:latest
    container_name: sovereign-node-exporter
    restart: unless-stopped
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    ports:
      - "9100:9100"
    networks:
      - sovereign-network

  # cAdvisor
  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    container_name: sovereign-cadvisor
    restart: unless-stopped
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:rw
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
      - /dev/disk/:/dev/disk:ro
    privileged: true
    devices:
      - /dev/kmsg
    ports:
      - "8080:8080"
    networks:
      - sovereign-network

  # GPU Exporter (if GPU available)
  gpu-exporter:
    image: mindprince/gpu-exporter:latest
    container_name: sovereign-gpu-exporter
    runtime: nvidia
    restart: unless-stopped
    ports:
      - "9445:9445"
    networks:
      - sovereign-network
    profiles:
      - gpu

volumes:
  prometheus_data:
    driver: local
  grafana_data:
    driver: local
  loki_data:
    driver: local

networks:
  sovereign-network:
    external: true
EOF

echo "✅ Monitoring and logging configuration created!"
echo ""
echo "📊 Services configured:"
echo "- Prometheus: http://localhost:9090"
echo "- Grafana: http://localhost:3000"
echo "- Loki: http://localhost:3100"
echo "- Node Exporter: http://localhost:9100"
echo "- cAdvisor: http://localhost:8080"
echo "- GPU Exporter: http://localhost:9445 (if GPU available)"
echo ""
echo "🚀 To start monitoring stack:"
echo "docker-compose -f docker-compose.monitoring.yml up -d"
