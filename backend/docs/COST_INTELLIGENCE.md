# Cost Intelligence

## Real-Time Cost Prediction

Predict exact cost before running any AI operation.

### Accuracy

- **Target**: 95% of predictions within 5% of actual cost
- **Confidence intervals**: Show uncertainty, not just point estimates
- **Learning**: Improves from historical data

### Usage

```bash
POST /api/v1/cost/predict
{
  "operation_type": "transcribe",
  "provider": "openai",
  "input_text": "Your text here...",
  "model": "whisper-1"
}

Response:
{
  "predicted_cost": "0.001234",
  "confidence_lower": "0.001100",
  "confidence_upper": "0.001400",
  "accuracy_score": 0.94,
  "alternative_providers": [
    {
      "provider": "huggingface",
      "cost": "0.000500",
      "savings_percent": 59.5
    }
  ]
}
```

### Cost History

```bash
GET /api/v1/cost/history?limit=100

Response:
[
  {
    "id": "...",
    "operation_type": "transcribe",
    "provider": "openai",
    "predicted_cost": "0.001234",
    "actual_cost": "0.001200",
    "prediction_error_percent": 2.8,
    "was_within_confidence": true
  }
]
```

## Intelligent Provider Routing

Automatically route requests to optimal provider.

### Routing Strategies

1. **Cost-optimized** - Lowest cost that meets quality threshold
2. **Quality-optimized** - Best quality within budget
3. **Speed-optimized** - Fastest within constraints
4. **Hybrid** - Balance cost, quality, speed

### Usage

```bash
POST /api/v1/routing/test
{
  "operation_type": "transcribe",
  "input_text": "Your audio transcript...",
  "constraints": {
    "strategy": "cost_optimized",
    "max_cost": "0.002",
    "min_quality": 0.8
  }
}

Response:
{
  "selected_provider": "huggingface",
  "reasoning": "Selected huggingface because it offers the lowest cost. Saves 59.5% vs openai.",
  "expected_cost": "0.000500",
  "expected_quality": 0.85,
  "expected_latency_ms": 2000,
  "alternatives": [...]
}
```

## Budget Management

Track and enforce budgets automatically.

### Create Budget

```bash
POST /api/v1/budget
{
  "budget_type": "monthly",
  "amount": "100.00",
  "alert_thresholds": [50, 80, 95]
}
```

### Check Budget Status

```bash
GET /api/v1/budget?budget_type=monthly

Response:
[
  {
    "budget_type": "monthly",
    "amount": "100.00",
    "current_spend": "45.23",
    "remaining": "54.77",
    "percent_used": 45.23,
    "forecast_exhaustion_date": "2026-02-15T00:00:00",
    "alert_level": "ok"
  }
]
```

### Budget Forecast

```bash
GET /api/v1/budget/forecast?budget_type=monthly

Response:
{
  "current_spend": "45.23",
  "budget_limit": "100.00",
  "remaining": "54.77",
  "forecast_exhaustion_date": "2026-02-15T00:00:00",
  "alert_level": "ok"
}
```

## Cost Allocation & Billing

Track costs per client/project for accurate billing.

### Allocate Cost

```bash
POST /api/v1/billing/allocate
{
  "operation_id": "...",
  "project_id": "project_a",
  "allocation_method": "percentage",
  "allocation_rules": {
    "project_a": 50,
    "project_b": 50
  }
}
```

### Generate Billing Report

```bash
GET /api/v1/billing/report?start_date=2026-01-01&end_date=2026-01-31

Response:
{
  "summary": {
    "total_operations": 150,
    "total_base_cost": "45.23",
    "total_markup": "9.05",
    "total_final_cost": "54.28"
  },
  "by_project": {
    "project_a": "27.14",
    "project_b": "27.14"
  },
  "line_items": [...]
}
```

## Precision Guarantees

- **Cost calculations**: Precise to 6 decimal places (0.000001)
- **Allocations**: Sum exactly equals total (no rounding errors)
- **Predictions**: Tracked and validated against actuals
- **Billing**: Accurate to the cent
