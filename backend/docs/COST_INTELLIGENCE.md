# Cost Intelligence

## Overview

BYOS AI's cost intelligence system does four things:
1. **Predicts** exact cost before you run an operation (95% accuracy ±5%)
2. **Routes** requests to the cheapest valid provider automatically
3. **Enforces** budget limits in real-time — stops spending when you hit your cap
4. **Allocates** costs to clients/projects for accurate billing at markup

---

## Cost Prediction

Know the cost before you commit.

### Request
```
POST /api/v1/cost/predict
{
  "operation_type": "inference",
  "provider": "openai",
  "input_text": "Summarise this contract...",
  "model": "gpt-4"
}
```

### Response
```json
{
  "predicted_cost": "0.002341",
  "confidence_lower": "0.002100",
  "confidence_upper": "0.002600",
  "accuracy_score": 0.94,
  "alternative_providers": [
    { "provider": "ollama", "cost": "0.000000", "savings_percent": 100.0 },
    { "provider": "groq",   "cost": "0.000180", "savings_percent": 92.3 }
  ]
}
```

### Accuracy Tracking
Every prediction is compared against the actual cost after execution. Results stored in `cost_predictions` table. The ML predictor trains on this historical data and improves over time.

```
GET /api/v1/cost/history?limit=100
→ [{
  "predicted_cost": "0.002341",
  "actual_cost": "0.002200",
  "prediction_error_percent": 6.0,
  "was_within_confidence": true
}]
```

---

## Intelligent Provider Routing

Automatically select the optimal provider for each request based on your constraints.

### Routing Strategies

| Strategy | Selection Logic |
|---|---|
| `cost_optimized` | Cheapest provider that meets `min_quality` floor |
| `quality_optimized` | Best quality score within `max_cost` budget |
| `speed_optimized` | Lowest expected latency within `max_cost` budget |
| `hybrid` | Weighted score across cost (40%), quality (40%), speed (20%) |

### Test Routing Decision
```
POST /api/v1/routing/test
{
  "operation_type": "inference",
  "constraints": {
    "strategy": "cost_optimized",
    "max_cost": "0.005",
    "min_quality": 0.80,
    "max_latency_ms": 5000
  }
}
→ {
  "selected_provider": "ollama",
  "reasoning": "ollama: $0.00 cost (free), quality 0.85 >= threshold 0.80, latency 1800ms",
  "expected_cost": "0.000000",
  "expected_quality_score": 0.85,
  "expected_latency_ms": 1800,
  "savings_vs_openai": "100%"
}
```

### Configure Workspace Routing Policy
```
POST /api/v1/routing/policy
{
  "strategy": "cost_optimized",
  "max_cost_per_call": "0.010",
  "min_quality_score": 0.75,
  "preferred_providers": ["ollama", "groq"],
  "excluded_providers": ["openai"]
}
```

---

## Budget Management

### Create a Budget
```
POST /api/v1/budget
{
  "budget_type": "monthly",    ← "monthly" | "weekly" | "daily"
  "amount": "100.00",
  "alert_thresholds": [50, 80, 95]   ← % points to trigger alerts
}
```

### Check Budget Status
```
GET /api/v1/budget?budget_type=monthly
→ {
  "amount": "100.00",
  "current_spend": "67.43",
  "remaining": "32.57",
  "percent_used": 67.43,
  "forecast_exhaustion_date": "2026-01-28T00:00:00",
  "alert_level": "warning"
}
```

**Alert levels:**
- `ok` — below first threshold
- `warning` — past first threshold
- `critical` — past 80% threshold
- `exhausted` — at or over 100%

### How Budget Enforcement Works

`BudgetCheckMiddleware` runs before every AI call:
1. Loads current spend for the workspace + budget type
2. Estimates cost of the pending operation
3. If `current_spend + estimated_cost > budget.amount` → returns HTTP 402
4. If `percent_used >= any threshold` → fires alert via `POST /api/v1/monitoring/alerts`

### Emergency Kill Switch
```
POST /api/v1/cost/kill-switch
{ "reason": "Investigating runaway usage" }
# Immediately blocks all AI calls for workspace — returns 402 on every request

DELETE /api/v1/cost/kill-switch
# Re-enable normal operation
```

---

## Cost Allocation & Client Billing

Tag AI costs to specific clients or projects, then generate invoice-ready billing reports.

### Allocate a Cost
```
POST /api/v1/billing/allocate
{
  "operation_id": "audit-log-uuid",
  "project_id": "client-acme",
  "allocation_method": "percentage",
  "allocation_rules": {
    "client-acme": 70,
    "client-globex": 30
  },
  "markup_percent": 35
}
```

### Get Billing Report
```
GET /api/v1/billing/report
  ?start_date=2026-01-01
  &end_date=2026-01-31
  &project_id=client-acme   ← optional filter

→ {
  "summary": {
    "total_operations": 8240,
    "total_base_cost": "34.82",
    "total_markup": "12.19",
    "total_final_cost": "47.01"
  },
  "by_project": {
    "client-acme": "32.91",
    "client-globex": "14.10"
  },
  "line_items": [...]
}
```

**Precision:** All calculations use `Decimal(10,6)` — precise to $0.000001. Allocation percentages always sum to exactly 100. No rounding errors when multiplied across thousands of operations.

---

## ML Cost Predictor (Autonomous)

The ML cost predictor (`core/autonomous/ml_models.py`) improves predictions over time by training on your actual usage:

```
POST /api/v1/autonomous/cost/predict
{
  "operation_type": "inference",
  "provider": "ollama",
  "input_tokens": 142,
  "estimated_output_tokens": 300
}
→ {
  "predicted_cost": "0.000000",
  "confidence_lower": "0.000000",
  "confidence_upper": "0.000001",
  "is_ml_prediction": true,
  "model_version": "v1.4",
  "training_samples": 847
}
```

Train on demand (also runs automatically on Celery schedule when `auto_training` feature flag is enabled):
```
POST /api/v1/autonomous/train
{ "min_samples": 100 }
```

---

## Savings Summary

Typical savings by routing scenario:

| Scenario | Old Cost | BYOS Cost | Savings |
|---|---|---|---|
| 10k inferences/day (GPT-4 → Ollama) | ~$150/day | $0/day | 100% |
| 10k inferences/day (GPT-3.5 → Ollama) | ~$15/day | $0/day | 100% |
| Mixed quality requirements (GPT-4 + fallback) | ~$80/day | ~$24/day | ~70% |
| Agency with markup on Ollama calls | $0 cost + 35% markup | Net positive | >100% ROI |
