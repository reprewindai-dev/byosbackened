# Veklom Backend Endpoint Inventory

Generated from Windsurf inspection of `apps/api/routers/`.

## Module: kill_switch (Cost Intelligence)
| Method | Path | Handler | Auth | Risk | Suggested Plan | Token Cost | Notes |
|--------|------|---------|------|------|----------------|------------|-------|
| POST | /cost/kill-switch | activate_kill_switch | Admin | sovereign | sovereign | 0 | Emergency cost control - blocks AI calls |
| DELETE | /cost/kill-switch | deactivate_kill_switch | Admin | sovereign | sovereign | 0 | Re-enable AI operations |
| GET | /cost/kill-switch/status | get_kill_switch_status | Admin | sovereign | sovereign | 0 | Check kill switch status |

## Module: locker_security (LockerPhycer Security)
| Method | Path | Handler | Auth | Risk | Suggested Plan | Token Cost | Notes |
|--------|------|---------|------|------|----------------|------------|-------|
| GET | /locker/security/events | list_security_events | Auth | sensitive | sovereign | 40 | List security events with filtering |
| GET | /locker/security/events/{id} | get_security_event | Auth | sensitive | sovereign | 40 | Get event by ID |
| POST | /locker/security/events | create_security_event | Auth | sensitive | sovereign | 40 | Create security event |
| PUT | /locker/security/events/{id}/assign | assign_security_event | Auth | sensitive | sovereign | 40 | Assign event to user |
| PUT | /locker/security/events/{id}/resolve | resolve_security_event | Admin | sensitive | sovereign | 40 | Resolve security event |
| GET | /locker/security/threats/stats | get_threat_stats | Auth | sensitive | sovereign | 40 | Get threat statistics |
| GET | /locker/security/controls | get_security_controls | Auth | sensitive | sovereign | 40 | Get security controls |
| POST | /locker/security/controls/{name} | toggle_security_control | Auth | sensitive | sovereign | 40 | Toggle security control |
| GET | /locker/security/dashboard | get_security_dashboard | Auth | sensitive | sovereign | 50 | Full security dashboard |

## Module: locker_monitoring (LockerPhycer Monitoring)
| Method | Path | Handler | Auth | Risk | Suggested Plan | Token Cost | Notes |
|--------|------|---------|------|------|----------------|------------|-------|
| GET | /locker/monitoring/status | get_system_status | Auth | authenticated | pro | 25 | Overall system status |
| GET | /locker/monitoring/metrics/performance | get_performance_metrics | Auth | authenticated | pro | 25 | Performance metrics |
| GET | /locker/monitoring/alerts/summary | get_alerts_summary | Auth | authenticated | pro | 25 | Alert summary |
| GET | /locker/monitoring/alerts | list_alerts | Auth | authenticated | pro | 25 | List alerts |
| POST | /locker/monitoring/alerts/{id}/resolve | resolve_alert | Auth | authenticated | pro | 25 | Resolve alert |
| GET | /locker/monitoring/health/detailed | get_detailed_health | Auth | authenticated | pro | 25 | Detailed health check |

## Module: admin
| Method | Path | Handler | Auth | Risk | Suggested Plan | Token Cost | Notes |
|--------|------|---------|------|------|----------------|------------|-------|
| GET | /admin/workspaces | list_workspaces | Superuser | internal-only | internal | 0 | List all workspaces |
| GET | /admin/workspaces/{id} | get_workspace | Admin | sensitive | sovereign | 0 | Get workspace details |
| PATCH | /admin/workspaces/{id} | update_workspace | Admin | sensitive | sovereign | 0 | Update workspace |
| DELETE | /admin/workspaces/{id} | delete_workspace | Superuser | internal-only | internal | 0 | Hard-delete workspace |
| GET | /admin/users | list_users | Admin | sensitive | sovereign | 0 | List users |
| POST | /admin/users | create_user | Admin | sensitive | sovereign | 0 | Create user |
| PATCH | /admin/users/{id} | update_user | Admin | sensitive | sovereign | 0 | Update user |
| DELETE | /admin/users/{id} | delete_user | Admin | sensitive | sovereign | 0 | Delete user |
| GET | /admin/overview | system_overview | Superuser | internal-only | internal | 0 | Platform-wide stats |

## Module: audit
| Method | Path | Handler | Auth | Risk | Suggested Plan | Token Cost | Notes |
|--------|------|---------|------|------|----------------|------------|-------|
| GET | /audit/logs | get_audit_logs | Auth | sensitive | sovereign | 30 | Query audit logs |
| GET | /audit/verify/{id} | verify_audit_log | Auth | sensitive | sovereign | 30 | Verify log integrity |
| POST | /audit/compliance-report | generate_compliance_report | Auth | sensitive | sovereign | 2500 | Generate compliance report |

## Module: auth
| Method | Path | Handler | Auth | Risk | Suggested Plan | Token Cost | Notes |
|--------|------|---------|------|------|----------------|------------|-------|
| POST | /auth/register | register | Public | public | public | 0 | Register workspace |
| POST | /auth/login | login | Public | public | public | 0 | Authenticate user |
| POST | /auth/refresh | refresh_token | Auth | authenticated | starter | 0 | Rotate access token |
| POST | /auth/logout | logout | Auth | authenticated | starter | 0 | Invalidate sessions |
| GET | /auth/me | me | Auth | authenticated | starter | 0 | Get user profile |
| POST | /auth/mfa/setup | mfa_setup | Auth | authenticated | starter | 0 | Setup MFA |
| POST | /auth/mfa/verify | mfa_verify | Auth | authenticated | starter | 0 | Verify MFA |
| DELETE | /auth/mfa/disable | mfa_disable | Auth | authenticated | starter | 0 | Disable MFA |
| POST | /auth/api-keys | create_api_key | Auth | authenticated | starter | 0 | Create API key |
| GET | /auth/api-keys | list_api_keys | Auth | authenticated | starter | 0 | List API keys |
| DELETE | /auth/api-keys/{id} | revoke_api_key | Auth | authenticated | starter | 0 | Revoke API key |

## Module: autonomous (ML/AI Optimization)
| Method | Path | Handler | Auth | Risk | Suggested Plan | Token Cost | Notes |
|--------|------|---------|------|------|----------------|------------|-------|
| POST | /autonomous/cost/predict | predict_cost_ml | Auth | paid | pro | 50 | ML cost prediction |
| POST | /autonomous/routing/select | select_provider_ml | Auth | paid | pro | 50 | ML provider selection |
| POST | /autonomous/routing/update | update_routing_outcome | Auth | paid | pro | 50 | Update routing outcome |
| GET | /autonomous/routing/stats | get_routing_stats | Auth | paid | pro | 25 | Routing statistics |
| POST | /autonomous/quality/predict | predict_quality_ml | Auth | paid | pro | 50 | Quality prediction |
| POST | /autonomous/quality/optimize | optimize_for_quality | Auth | paid | sovereign | 50 | Optimize for quality |
| POST | /autonomous/quality/failure-risk | predict_failure_risk | Auth | paid | sovereign | 50 | Predict failure risk |
| POST | /autonomous/train | train_models | Auth | paid | enterprise | 50 | Train ML models |

## Module: billing
| Method | Path | Handler | Auth | Risk | Suggested Plan | Token Cost | Notes |
|--------|------|---------|------|------|----------------|------------|-------|
| POST | /billing/allocate | allocate_cost | Auth | paid | pro | 30 | Allocate cost |
| GET | /billing/report | generate_billing_report | Auth | paid | pro | 30 | Generate billing report |
| GET | /billing/breakdown | get_cost_breakdown | Auth | paid | pro | 30 | Cost breakdown |

## Module: budget
| Method | Path | Handler | Auth | Risk | Suggested Plan | Token Cost | Notes |
|--------|------|---------|------|------|----------------|------------|-------|
| POST | /budget | create_budget | Auth | paid | pro | 25 | Create/update budget |
| GET | /budget | get_budget_status | Auth | paid | pro | 25 | Get budget status |
| GET | /budget/forecast | get_budget_forecast | Auth | paid | pro | 25 | Budget forecast |

## Module: compliance
| Method | Path | Handler | Auth | Risk | Suggested Plan | Token Cost | Notes |
|--------|------|---------|------|------|----------------|------------|-------|
| GET | /compliance/regulations | list_regulations | Auth | authenticated | starter | 10 | List regulations |
| POST | /compliance/check | check_compliance | Auth | sensitive | sovereign | 250 | Check compliance |
| POST | /compliance/report | generate_compliance_report | Auth | sensitive | sovereign | 2500 | Generate report |

## Module: content_safety
| Method | Path | Handler | Auth | Risk | Suggested Plan | Token Cost | Notes |
|--------|------|---------|------|------|----------------|------------|-------|
| POST | /content-safety/scan | scan_content | Auth | authenticated | starter | 25 | Scan content |
| POST | /content-safety/scan/file | scan_file | Auth | authenticated | starter | 40 | Scan uploaded file |
| POST | /content-safety/age-verification/initiate | initiate_age_verification | Auth | authenticated | starter | 0 | Initiate age verification |
| POST | /content-safety/age-verification/confirm | confirm_age_verification | Auth | authenticated | starter | 0 | Confirm age verification |
| GET | /content-safety/age-verification/status | age_verification_status | Auth | authenticated | starter | 0 | Check age verification |
| GET | /content-safety/logs | content_filter_logs | Admin | sensitive | sovereign | 40 | View content logs |

## Module: cost
| Method | Path | Handler | Auth | Risk | Suggested Plan | Token Cost | Notes |
|--------|------|---------|------|------|----------------|------------|-------|
| POST | /cost/predict | predict_cost | Auth | authenticated | starter | 25 | Predict operation cost |
| GET | /cost/history | get_cost_history | Auth | authenticated | starter | 25 | Cost prediction history |

## Module: exec_router (LLM Execution)
| Method | Path | Handler | Auth | Risk | Suggested Plan | Token Cost | Notes |
|--------|------|---------|------|------|----------------|------------|-------|
| POST | /v1/exec | exec_llm | API Key | paid | starter | Variable | LLM execution (variable cost) |
| GET | /status | system_status | Public | public | public | 0 | System health check |

## Module: explainability
| Method | Path | Handler | Auth | Risk | Suggested Plan | Token Cost | Notes |
|--------|------|---------|------|------|----------------|------------|-------|
| POST | /explain/routing | explain_routing | Auth | paid | pro | 30 | Explain routing decision |
| POST | /explain/cost | explain_cost | Auth | paid | pro | 30 | Explain cost prediction |

## Module: insights
| Method | Path | Handler | Auth | Risk | Suggested Plan | Token Cost | Notes |
|--------|------|---------|------|------|----------------|------------|-------|
| GET | /insights/savings | get_savings | Auth | paid | pro | 25 | Get savings |
| GET | /insights/savings/projected | get_projected_savings | Auth | paid | pro | 25 | Projected savings |
| GET | /insights/summary | get_insights_summary | Auth | paid | pro | 25 | Insights summary |

## Module: plugins
| Method | Path | Handler | Auth | Risk | Suggested Plan | Token Cost | Notes |
|--------|------|---------|------|------|----------------|------------|-------|
| GET | /plugins | list_plugins | Auth | authenticated | starter | 10 | List plugins |
| POST | /plugins/{name}/enable | enable_plugin | Auth | paid | sovereign | 40 | Enable plugin |
| POST | /plugins/{name}/disable | disable_plugin | Auth | paid | sovereign | 40 | Disable plugin |
| GET | /plugins/{name}/docs | get_plugin_docs | Auth | authenticated | starter | 10 | Plugin docs |

## Module: privacy
| Method | Path | Handler | Auth | Risk | Suggested Plan | Token Cost | Notes |
|--------|------|---------|------|------|----------------|------------|-------|
| POST | /privacy/export | export_user_data | Auth | sensitive | sovereign | 2500 | GDPR data export |
| POST | /privacy/delete | delete_user_data | Auth | sensitive | sovereign | 2500 | GDPR data deletion |
| POST | /privacy/detect-pii | detect_pii_endpoint | Auth | authenticated | starter | 25 | Detect PII |
| POST | /privacy/mask-pii | mask_pii_endpoint | Auth | authenticated | starter | 25 | Mask PII |

## Module: routing
| Method | Path | Handler | Auth | Risk | Suggested Plan | Token Cost | Notes |
|--------|------|---------|------|------|----------------|------------|-------|
| POST | /routing/policy | create_routing_policy | Auth | paid | pro | 25 | Create routing policy |
| GET | /routing/policy | get_routing_policy | Auth | authenticated | starter | 25 | Get routing policy |
| POST | /routing/test | test_routing | Auth | paid | pro | 25 | Test routing |

## Module: security_suite
| Method | Path | Handler | Auth | Risk | Suggested Plan | Token Cost | Notes |
|--------|------|---------|------|------|----------------|------------|-------|
| GET | /security/events | list_events | Auth | sensitive | sovereign | 40 | List security events |
| GET | /security/events/{id} | get_event | Auth | sensitive | sovereign | 40 | Get event |
| POST | /security/events | create_event | Auth | sensitive | sovereign | 40 | Create event |
| PUT | /security/events/{id}/resolve | resolve_event | Admin | sensitive | sovereign | 40 | Resolve event |
| PUT | /security/events/{id}/assign | assign_event | Admin | sensitive | sovereign | 40 | Assign event |
| GET | /security/stats | get_stats | Auth | sensitive | sovereign | 40 | Security stats |
| GET | /security/dashboard | security_dashboard | Auth | sensitive | sovereign | 50 | Security dashboard |
| GET | /security/alerts | list_alerts | Auth | sensitive | sovereign | 40 | List alerts |
| PUT | /security/alerts/{id}/acknowledge | acknowledge_alert | Auth | sensitive | sovereign | 40 | Acknowledge alert |

## Module: monitoring_suite
| Method | Path | Handler | Auth | Risk | Suggested Plan | Token Cost | Notes |
|--------|------|---------|------|------|----------------|------------|-------|
| GET | /monitoring/health | system_health | Auth | authenticated | starter | 10 | Full system health |
| GET | /monitoring/metrics | get_metrics | Auth | paid | pro | 25 | Workspace metrics |
| GET | /monitoring/dashboard | monitoring_dashboard | Auth | paid | pro | 25 | Monitoring dashboard |
| POST | /monitoring/metrics/record | record_metric | Admin | internal-only | internal | 0 | Record custom metric |
| GET | /monitoring/metrics/history | metric_history | Auth | paid | pro | 25 | Metric history |

## Module: subscriptions
| Method | Path | Handler | Auth | Risk | Suggested Plan | Token Cost | Notes |
|--------|------|---------|------|------|----------------|------------|-------|
| GET | /subscriptions/plans | list_plans | Public | public | public | 0 | List subscription plans |
| GET | /subscriptions/current | current_subscription | Auth | authenticated | starter | 0 | Get current subscription |
| POST | /subscriptions/checkout | create_checkout | Auth | authenticated | starter | 0 | Create Stripe checkout |
| GET | /subscriptions/session/{id} | check_session | Auth | authenticated | starter | 0 | Check session status |
| POST | /subscriptions/portal | billing_portal | Auth | authenticated | starter | 0 | Stripe customer portal |
| POST | /subscriptions/webhook | stripe_webhook | Public | public | public | 0 | Stripe webhook handler |

## Module: health (Basic)
| Method | Path | Handler | Auth | Risk | Suggested Plan | Token Cost | Notes |
|--------|------|---------|------|------|----------------|------------|-------|
| GET | /health | health_check | Public | public | public | 0 | Basic health check |

## Module: metrics (Prometheus)
| Method | Path | Handler | Auth | Risk | Suggested Plan | Token Cost | Notes |
|--------|------|---------|------|------|----------------|------------|-------|
| GET | /metrics | get_metrics | Public | public | public | 0 | Prometheus metrics |

---

## Token Cost Reference

| Credit Class | Token Cost | Description |
|--------------|------------|-------------|
| Free metadata | 0 | Health, public pricing, marketplace browse |
| Low-cost control | 0-10 | Auth, profile, basic status |
| Standard API | 25-100 | Search, suggestions, basic metrics, cost predict |
| AI/model route | Variable | Routing, exec, content scan, transcription |
| Heavy workflow | Variable + min | Job, file scan, extract, upload processing |
| Compliance/audit | 250-2500 | Compliance report, audit verification, export |
| Enterprise control | Plan-gated | Kill switch, admin, custom training |

## Plan Entitlements Summary

| Module | Starter | Pro | Sovereign | Enterprise |
|--------|---------|-----|-----------|------------|
| kill_switch | ❌ | ❌ | ✅ | ✅ |
| locker_security | ❌ | ❌ | ✅ | ✅ |
| locker_monitoring | Limited | ✅ | ✅ | ✅ |
| admin | ❌ | ❌ | Limited | ✅ |
| audit | Limited | Limited | ✅ | ✅ |
| auth | ✅ | ✅ | ✅ | ✅ |
| autonomous | Limited | ✅ | ✅ | ✅ |
| billing | Limited | ✅ | ✅ | ✅ |
| budget | Limited | ✅ | ✅ | ✅ |
| compliance | ❌ | Limited | ✅ | ✅ |
| content_safety | ✅ | ✅ | ✅ | ✅ |
| cost | ✅ | ✅ | ✅ | ✅ |
| exec_router | Limited | ✅ | ✅ | ✅ |
| explainability | ❌ | ✅ | ✅ | ✅ |
| insights | Limited | ✅ | ✅ | ✅ |
| plugins | Limited | Limited | ✅ | ✅ |
| privacy | Limited | Limited | ✅ | ✅ |
| routing | Limited | ✅ | ✅ | ✅ |
| security_suite | ❌ | Limited | ✅ | ✅ |
| monitoring_suite | Limited | ✅ | ✅ | ✅ |
| subscriptions | ✅ | ✅ | ✅ | ✅ |

---
*Generated: 2026-04-27*
