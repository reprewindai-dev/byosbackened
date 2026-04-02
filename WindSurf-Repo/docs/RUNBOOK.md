# Production Runbook

## Emergency Procedures

### 1. Rollback Steps

#### Rollback Database Migration
```bash
# Connect to production database
cd backend
alembic downgrade -1

# Verify rollback
alembic current
```

#### Rollback ML Model
```python
from core.autonomous.ml_models.cost_predictor import get_cost_predictor_ml
from db.session import SessionLocal

db = SessionLocal()
cost_predictor = get_cost_predictor_ml()

# Rollback to previous model version
result = cost_predictor.rollback_to_previous_model(
    db=db,
    workspace_id="workspace_id",  # or None for all workspaces
)
```

### 2. Disable Routing

#### Disable Autonomous Routing
```bash
# Set environment variable
export AUTONOMOUS_ROUTING_ENABLED=false

# Or via Python
from core.autonomous.feature_flags import get_feature_flags
flags = get_feature_flags()
flags.disable("autonomous_routing_enabled")
```

#### Disable ML Routing Optimizer
```bash
export ML_ROUTING_OPTIMIZER_ENABLED=false
```

#### Disable Edge Routing
```bash
export EDGE_ROUTING_ENABLED=false
```

### 3. Disable Retraining

```bash
export MODEL_RETRAINING_ENABLED=false
```

This prevents:
- Automatic model retraining
- Canary deployments
- Model version updates

### 4. Provider Outage Procedure

#### Disable Specific Provider
```python
from core.providers.circuit_breaker import get_circuit_breaker

cb = get_circuit_breaker()
cb.trip("openai")  # Trip circuit breaker for provider
```

#### Enable Provider After Recovery
```python
cb.reset("openai")  # Reset circuit breaker
```

### 5. Cost Emergency

#### Enable Cost Kill Switch
```python
from core.cost_intelligence.kill_switch import get_cost_kill_switch

kill_switch = get_cost_kill_switch()
kill_switch.enable()  # Enforce hard caps
```

#### Disable All Autonomous Features (Emergency)
```python
from core.autonomous.feature_flags import get_feature_flags

flags = get_feature_flags()
flags.disable_all_autonomous()  # Nuclear option
```

### 6. Queue Emergency

#### Check Queue Backlog
```python
from core.autonomous.queuing.backlog_monitor import get_backlog_monitor

monitor = get_backlog_monitor()
stats = monitor.get_backlog_stats()
print(stats)
```

#### Enable Load Shedding
Load shedding is automatic when queue depth > 2000 items.

### 7. Anomaly Remediation

#### Disable Auto-Remediation
```bash
export AUTO_REMEDIATION_ENABLED=false
```

#### Manual Remediation
```python
from core.autonomous.anomaly.remediator import get_auto_remediator
from db.session import SessionLocal

db = SessionLocal()
remediator = get_auto_remediator()

# Remediate specific anomaly
remediator.remediate(
    workspace_id="workspace_id",
    anomalies=[{
        "type": "cost_spike",
        "severity": "high",
        "message": "Cost spike detected",
    }],
    db=db,
)
```

## Monitoring & Dashboards

### Prometheus Metrics
- URL: `http://localhost:9090/metrics`
- Key metrics:
  - `autonomous_cost_total` - Total cost per workspace
  - `autonomous_latency_p95` - P95 latency
  - `routing_decisions_total` - Routing decisions
  - `anomalies_detected_total` - Anomalies detected
  - `queue_depth` - Queue depth per operation type

### Grafana Dashboards (if configured)
- Cost Dashboard: `/grafana/dashboards/cost`
- Latency Dashboard: `/grafana/dashboards/latency`
- Routing Dashboard: `/grafana/dashboards/routing`
- Anomaly Dashboard: `/grafana/dashboards/anomaly`

### Logs
- Application logs: Check container logs or log aggregation system
- Key log patterns:
  - `ERROR` - Errors requiring attention
  - `CRITICAL` - Critical issues (cost caps, outages)
  - `WARNING` - Warnings (budget alerts, anomalies)

## Alert Channels

### Alert Configuration
Alerts are sent via `core/incident/alerting.py`:
- Email (if configured)
- Slack webhook (if configured)
- PagerDuty (if configured)

### Test Alert
```python
from core.incident.alerting import send_alert

send_alert(
    alert_type="test",
    severity="low",
    message="Test alert - verify notification channel",
    workspace_id=None,
)
```

## Backup & Restore

### Backup Database
```bash
# PostgreSQL backup
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME > backup_$(date +%Y%m%d_%H%M%S).sql

# S3/MinIO backup (ML models)
aws s3 sync s3://$S3_BUCKET/ml_models/ ./backup/ml_models/
```

### Restore Database
```bash
# Restore PostgreSQL
psql -h $DB_HOST -U $DB_USER -d $DB_NAME < backup_YYYYMMDD_HHMMSS.sql

# Restore ML models
aws s3 sync ./backup/ml_models/ s3://$S3_BUCKET/ml_models/
```

### Smoke Test Restore
```bash
# Run restore smoke test
python backend/tests/backup/test_restore_smoke.py
```

## Feature Flags

### List All Flags
```python
from core.autonomous.feature_flags import get_feature_flags

flags = get_feature_flags()
print(flags.get_all_flags())
```

### Environment Variables
All feature flags can be controlled via environment variables:
- `AUTONOMOUS_ROUTING_ENABLED=true/false`
- `ML_COST_PREDICTION_ENABLED=true/false`
- `ML_ROUTING_OPTIMIZER_ENABLED=true/false`
- `MODEL_RETRAINING_ENABLED=true/false`
- `CANARY_DEPLOYMENT_ENABLED=true/false`
- `AUTO_REMEDIATION_ENABLED=true/false`
- `EDGE_ROUTING_ENABLED=true/false`
- `TRAFFIC_PREDICTION_ENABLED=true/false`

## Cost Guardrails

### Budget Caps
- Global daily cap: `GLOBAL_DAILY_COST_CAP` (default: $10,000)
- Per-workspace daily cap: `DEFAULT_WORKSPACE_DAILY_CAP` (default: $1,000)
- Kill switch: `COST_KILL_SWITCH_ENABLED=true/false`

### Check Current Spend
```python
from core.cost_intelligence.budget_tracker import BudgetTracker
from db.session import SessionLocal

db = SessionLocal()
tracker = BudgetTracker()

check = tracker.check_budget(
    db=db,
    workspace_id="workspace_id",
    operation_cost=Decimal("0"),
    budget_type="daily",
)
print(f"Current spend: ${check.current_spend} / ${check.budget_limit}")
```

## Troubleshooting

### High Latency
1. Check queue depth: `monitor.get_backlog_stats()`
2. Check provider health: `cb.get_status("provider_name")`
3. Check edge routing: `edge_routing_enabled` flag
4. Review tracing: Check trace IDs in logs

### High Costs
1. Check budget caps: `kill_switch.check_workspace_cap()`
2. Review routing decisions: Check `/api/v1/autonomous/routing/stats`
3. Disable expensive providers: Trip circuit breaker
4. Enable cost kill switch: `kill_switch.enable()`

### Model Degradation
1. Check drift detection: `drift_detector.detect_drift()`
2. Disable canary: `CANARY_DEPLOYMENT_ENABLED=false`
3. Rollback model: `cost_predictor.rollback_to_previous_model()`
4. Disable retraining: `MODEL_RETRAINING_ENABLED=false`

### Anomaly Spam
1. Review anomaly detector: Check detection thresholds
2. Disable auto-remediation: `AUTO_REMEDIATION_ENABLED=false`
3. Review anomaly logs: Check `Anomaly` table

## Contact & Escalation

- On-call engineer: Check PagerDuty
- Slack channel: `#backend-alerts`
- Email: `backend-team@company.com`

## Quick Reference

| Action | Command/Code |
|--------|-------------|
| Disable all autonomous | `flags.disable_all_autonomous()` |
| Enable cost kill switch | `kill_switch.enable()` |
| Rollback migration | `alembic downgrade -1` |
| Rollback model | `cost_predictor.rollback_to_previous_model()` |
| Check queue depth | `monitor.get_backlog_stats()` |
| Test alert | `send_alert(alert_type="test", ...)` |
| Disable routing | `export AUTONOMOUS_ROUTING_ENABLED=false` |
| Disable retraining | `export MODEL_RETRAINING_ENABLED=false` |
