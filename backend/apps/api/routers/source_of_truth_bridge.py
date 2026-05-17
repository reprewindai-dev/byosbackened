"""Source-of-truth routing matrix compatibility layer.

This router contains only non-native frontend matrix endpoint adapters where
backend path contracts differ. Supported matrix endpoints are forwarded to
canonical backend routes. Matrix routes without backend contracts return
`No route found`.
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import Response

from core.config import get_settings

router = APIRouter(tags=["source-of-truth-bridge"])


_DISALLOWED_PROXY_HEADERS = {
    "host",
    "accept-encoding",
    "connection",
    "keep-alive",
    "upgrade",
    "te",
    "proxy-connection",
    "transfer-encoding",
}


def _no_route_found() -> None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No route found")


def _clean_headers(request: Request) -> dict[str, str]:
    return {
        name: value
        for name, value in request.headers.items()
        if name.lower() not in _DISALLOWED_PROXY_HEADERS
    }


def _clean_response_headers(response_headers: httpx.Headers) -> dict[str, str]:
    return {
        name: value
        for name, value in response_headers.items()
        if name.lower()
        not in {
            "content-encoding",
            "transfer-encoding",
            "connection",
            "server",
        }
    }


def _mounted_target_path(target_path: str) -> str:
    settings = get_settings()
    api_prefix = settings.api_prefix.rstrip("/")
    if not target_path.startswith("/"):
        return f"{api_prefix}/{target_path}"
    if target_path == api_prefix or target_path.startswith(f"{api_prefix}/"):
        return target_path
    if target_path.startswith("/api/"):
        return target_path
    return f"{api_prefix}{target_path}"


async def _proxy_request(
    request: Request,
    target_path: str,
    method: str | None = None,
    override_body: dict[str, Any] | str | bytes | None = None,
) -> Response:
    # ── Self-loop guard: if we are already inside a bridge proxy, stop. ──
    if request.headers.get("x-bridge-proxy") == "1":
        return Response(
            content=json.dumps({"detail": "Bridge loop detected"}),
            status_code=508,
            media_type="application/json",
        )

    start = time.perf_counter()

    mounted_target_path = _mounted_target_path(target_path)
    method = (method or request.method).upper()
    headers = _clean_headers(request)
    # Tag the proxied request so we can detect loops
    headers["x-bridge-proxy"] = "1"
    body: bytes | None = None

    if isinstance(override_body, (dict, list)):
        body = json.dumps(override_body).encode("utf-8")
        headers.setdefault("content-type", "application/json")
    elif isinstance(override_body, str):
        body = override_body.encode("utf-8")
    elif isinstance(override_body, bytes):
        body = override_body
    elif method not in {"GET", "HEAD"}:
        body = await request.body()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=request.app),
        base_url="http://testserver",
        timeout=10.0,
    ) as client:
        proxied = await client.request(
            method=method,
            url=mounted_target_path,
            headers=headers,
            params=request.query_params,
            content=body,
        )

    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    response_headers = _clean_response_headers(proxied.headers)
    response_headers["x-route-source"] = "source-of-truth-bridge"
    response_headers["x-route-source-time-ms"] = str(elapsed_ms)
    response_headers["x-route-mapped-to"] = mounted_target_path

    if proxied.status_code == status.HTTP_404_NOT_FOUND:
        return Response(
            content=json.dumps({"detail": "No route found"}),
            status_code=status.HTTP_404_NOT_FOUND,
            headers=response_headers,
            media_type="application/json",
        )

    return Response(
        content=proxied.content,
        status_code=proxied.status_code,
        headers=response_headers,
        media_type=proxied.headers.get("content-type"),
    )


@router.get("/auth/github")
async def matrix_auth_github(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/auth/github/login")


@router.get("/auth/github/callback")
async def matrix_auth_github_callback(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/auth/github/callback")


@router.post("/auth/password/reset")
async def matrix_auth_password_reset() -> None:
    _no_route_found()


@router.post("/auth/password/change")
async def matrix_auth_password_change() -> None:
    _no_route_found()


@router.get("/workspace")
async def matrix_workspace_summary(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/workspace/overview")


@router.get("/workspace/")
async def matrix_workspace_root(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/workspace/overview")


@router.post("/workspace/api-keys")
async def matrix_workspace_api_keys_create(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/auth/api-keys")


@router.delete("/workspace/api-keys/{api_key_id}")
async def matrix_workspace_api_keys_delete(request: Request, api_key_id: str) -> Response:
    return await _proxy_request(
        request=request,
        target_path=f"/auth/api-keys/{api_key_id}",
        method="DELETE",
    )


@router.get("/workspace/api-keys")
async def matrix_workspace_api_keys_list(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/auth/api-keys")


@router.post("/workspace/models")
async def matrix_workspace_models_create() -> None:
    _no_route_found()


@router.delete("/workspace/models/{model_id}")
async def matrix_workspace_models_delete(model_id: str) -> None:
    _no_route_found()


@router.get("/workspace/models")
async def matrix_workspace_models_get(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/workspace/models")


@router.get("/workspace/members")
async def matrix_workspace_members_list(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/workspace/members")


@router.delete("/workspace/members/{member_id}")
async def matrix_workspace_member_delete(member_id: str, request: Request) -> Response:
    return await _proxy_request(
        request=request,
        target_path=f"/admin/users/{member_id}",
        method="DELETE",
    )


@router.get("/workspace/usage")
async def matrix_workspace_usage(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/workspace/analytics/summary")


@router.get("/billing/wallet")
async def matrix_billing_wallet(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/wallet/balance")


@router.get("/billing/transactions")
async def matrix_billing_transactions(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/wallet/transactions")


@router.post("/billing/topup")
async def matrix_billing_topup(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/wallet/topup/checkout")


@router.get("/billing/topup")
async def matrix_billing_topup_options(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/wallet/topup/options")


@router.get("/token-wallet/balance")
async def matrix_token_wallet_balance(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/wallet/balance")


@router.get("/token-wallet/history")
async def matrix_token_wallet_history(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/wallet/transactions")


@router.get("/subscriptions/plans")
async def matrix_subscriptions_plans(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/subscriptions/plans")


@router.get("/subscriptions/current")
async def matrix_subscriptions_current(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/subscriptions/current")


@router.post("/subscriptions/checkout")
async def matrix_subscriptions_checkout(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/subscriptions/checkout")


@router.post("/subscriptions/webhook")
async def matrix_subscriptions_webhook(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/subscriptions/webhook")


@router.post("/ai/exec")
async def matrix_ai_exec(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/ai/complete")


@router.post("/v1/exec")
async def matrix_v1_exec(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/v1/exec")


@router.get("/ai/models")
async def matrix_ai_models(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/workspace/models")


@router.post("/ai/stream")
async def matrix_ai_stream() -> None:
    _no_route_found()


@router.get("/ai/conversation/{conversation_id}")
async def matrix_ai_conversation_get(conversation_id: str) -> None:
    _no_route_found()


@router.delete("/ai/conversation/{conversation_id}")
async def matrix_ai_conversation_delete(conversation_id: str) -> None:
    _no_route_found()


@router.post("/exec/run")
async def matrix_exec_run(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/ai/complete")


@router.get("/exec/providers")
async def matrix_exec_providers(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/routing/policy")


@router.get("/marketplace/downloads/{download_id}")
async def matrix_marketplace_download(request: Request, download_id: str) -> Response:
    return await _proxy_request(
        request=request,
        target_path=f"/marketplace/files/{download_id}/download",
    )


@router.get("/listings")
async def matrix_public_listing_list(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/marketplace/listings")


@router.post("/marketplace/listings")
async def matrix_marketplace_listing_create(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/marketplace/listings/create")


@router.post("/marketplace/checkout")
async def matrix_marketplace_checkout(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/marketplace/payments/create-checkout")


@router.get("/marketplace/orders")
async def matrix_marketplace_orders(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/marketplace/orders/me")


@router.get("/routing/rules")
async def matrix_routing_rules_get(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/routing/policy")


@router.post("/routing/rules")
async def matrix_routing_rules_create(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/routing/policy")


@router.get("/routing/providers")
async def matrix_routing_providers_get(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/routing/policy")


@router.put("/routing/providers/{provider_id}")
async def matrix_routing_provider_update(provider_id: str) -> None:
    _no_route_found()


@router.post("/routing/test")
async def matrix_routing_test(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/routing/test")


@router.post("/plugins/{plugin_id}/install")
async def matrix_plugins_install(request: Request, plugin_id: str) -> Response:
    return await _proxy_request(
        request=request,
        target_path=f"/plugins/{plugin_id}/enable",
        method="POST",
    )


@router.delete("/plugins/{plugin_id}/uninstall")
async def matrix_plugins_uninstall(request: Request, plugin_id: str) -> Response:
    return await _proxy_request(
        request=request,
        target_path=f"/plugins/{plugin_id}/disable",
        method="POST",
    )


@router.get("/plugins/available")
async def matrix_plugins_available(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/plugins")


@router.get("/security/zero-trust/status")
async def matrix_security_zero_trust_status(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/security/dashboard")


@router.get("/security/zero-trust/policies")
async def matrix_security_zero_trust_policies(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/security/dashboard")


@router.post("/security/zero-trust/policies")
async def matrix_security_zero_trust_policies_create() -> None:
    _no_route_found()


@router.get("/security/threats")
async def matrix_security_threats(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/security/events")


@router.get("/security/locker")
async def matrix_security_locker(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/locker/security/dashboard")


@router.get("/kill-switch/status")
async def matrix_kill_switch_status(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/cost/kill-switch/status")


@router.post("/kill-switch/activate")
async def matrix_kill_switch_activate(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/cost/kill-switch", method="POST")


@router.post("/kill-switch/deactivate")
async def matrix_kill_switch_deactivate(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/cost/kill-switch", method="DELETE")


@router.get("/compliance/reports")
async def matrix_compliance_reports_list() -> None:
    _no_route_found()


@router.get("/compliance/reports/{report_id}")
async def matrix_compliance_report_download(report_id: str) -> None:
    _no_route_found()


@router.get("/compliance/regulations")
async def matrix_compliance_regulations(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/compliance/regulations")


@router.post("/compliance/check")
async def matrix_compliance_check(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/compliance/check")


@router.get("/privacy/rules")
async def matrix_privacy_rules_list() -> None:
    _no_route_found()


@router.post("/privacy/rules")
async def matrix_privacy_rules_create() -> None:
    _no_route_found()


@router.put("/privacy/rules/{rule_id}")
async def matrix_privacy_rules_update(rule_id: str) -> None:
    _no_route_found()


@router.delete("/privacy/rules/{rule_id}")
async def matrix_privacy_rules_delete(rule_id: str) -> None:
    _no_route_found()


@router.post("/privacy/scan")
async def matrix_privacy_scan(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/privacy/detect-pii")


@router.get("/content-safety/rules")
async def matrix_content_safety_rules_list() -> None:
    _no_route_found()


@router.post("/content-safety/rules")
async def matrix_content_safety_rules_create() -> None:
    _no_route_found()


@router.post("/content-safety/test")
async def matrix_content_safety_test(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/content-safety/scan")


@router.get("/content-safety/violations")
async def matrix_content_safety_violations(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/content-safety/logs")


@router.get("/insights")
async def matrix_insights_dashboard(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/insights/summary")


@router.get("/insights/trends")
async def matrix_insights_trends(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/insights/savings/projected")


@router.get("/insights/recommendations")
async def matrix_insights_recommendations(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/suggestions")


@router.get("/budget/caps")
async def matrix_budget_caps_get(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/budget")


@router.post("/budget/caps")
async def matrix_budget_caps_post(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/budget")


@router.put("/budget/caps/{cap_id}")
async def matrix_budget_caps_put(cap_id: str) -> None:
    _no_route_found()


@router.get("/cost/breakdown")
async def matrix_cost_breakdown(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/billing/breakdown")


@router.get("/cost/forecast")
async def matrix_cost_forecast(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/budget/forecast")


@router.get("/monitoring/overview")
async def matrix_monitoring_overview(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/monitoring/dashboard")


@router.get("/monitoring/metrics")
async def matrix_monitoring_metrics(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/monitoring/metrics")


@router.get("/monitoring/health")
async def matrix_monitoring_health(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/monitoring/health")


@router.get("/monitoring/alerts")
async def matrix_monitoring_alerts_get(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/monitoring/alerts")


@router.post("/monitoring/alerts")
async def matrix_monitoring_alerts_post(request: Request) -> Response:
    return await _proxy_request(
        request=request,
        target_path="/monitoring/alerts",
        method="POST",
    )


@router.get("/monitoring/logs")
async def matrix_monitoring_logs(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/monitoring/logs")


@router.get("/job")
async def matrix_job_list(request: Request) -> Response:
    return await _proxy_request(
        request=request,
        target_path="/jobs",
    )


@router.get("/job/{job_id}")
async def matrix_job_get(request: Request, job_id: str) -> Response:
    return await _proxy_request(request=request, target_path=f"/jobs/{job_id}")


@router.post("/job/{job_id}/cancel")
async def matrix_job_cancel(request: Request, job_id: str) -> Response:
    return await _proxy_request(
        request=request,
        target_path=f"/jobs/{job_id}/cancel",
        method="POST",
    )


@router.post("/pipelines/{pipeline_id}/run")
async def matrix_pipelines_run(request: Request, pipeline_id: str) -> Response:
    return await _proxy_request(
        request=request,
        target_path=f"/pipelines/{pipeline_id}/execute",
    )


@router.get("/pipelines")
async def matrix_pipelines_list(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/pipelines")


@router.post("/pipelines")
async def matrix_pipelines_create(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/pipelines", method="POST")


@router.put("/admin/users/{user_id}")
async def matrix_admin_user_update(request: Request, user_id: str) -> Response:
    return await _proxy_request(
        request=request,
        target_path=f"/admin/users/{user_id}",
        method="PATCH",
    )


@router.get("/admin/stats")
async def matrix_admin_stats(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/admin/overview")


@router.get("/admin/users")
async def matrix_admin_users_list(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/admin/users")


@router.delete("/admin/users/{user_id}")
async def matrix_admin_user_delete(request: Request, user_id: str) -> Response:
    return await _proxy_request(
        request=request,
        target_path=f"/admin/users/{user_id}",
        method="DELETE",
    )


@router.post("/admin/impersonate/{user_id}")
async def matrix_admin_impersonate(user_id: str) -> None:
    _no_route_found()


@router.get("/uacp/v0")
async def matrix_uacp_v0(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/internal/uacp/summary")


@router.get("/uacp/v1")
async def matrix_uacp_v1(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/internal/uacp/events")


@router.get("/uacp/v2")
async def matrix_uacp_v2(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/internal/uacp/event-stream")


@router.get("/uacp/v3")
async def matrix_uacp_v3(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/internal/uacp/monitoring")


@router.get("/uacp/v4")
async def matrix_uacp_v4(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/internal/uacp/security")


@router.get("/operators")
async def matrix_operators_overview(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/internal/operators/overview")


@router.get("/operators/digest")
async def matrix_operators_digest(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/internal/operators/digest")


@router.post("/operators/watch")
async def matrix_operators_watch(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/internal/operators/watch")


@router.post("/operators/qstash/enqueue")
async def matrix_operators_qstash_enqueue(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/internal/operators/qstash/enqueue")


@router.post("/operators/workflows/uacp-maintenance/trigger")
async def matrix_operators_uacp_maintenance(request: Request) -> Response:
    return await _proxy_request(
        request=request,
        target_path="/internal/operators/workflows/uacp-maintenance/trigger",
    )


@router.get("/operators/workers")
async def matrix_operators_workers(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/internal/operators/workers")


@router.get("/operators/registry")
async def matrix_operators_registry(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/internal/operators/registry")


@router.get("/operators/workers/{worker_id}")
async def matrix_operators_worker(request: Request, worker_id: str) -> Response:
    return await _proxy_request(
        request=request,
        target_path=f"/internal/operators/workers/{worker_id}",
    )


@router.post("/operators/workers/{worker_id}/heartbeat")
async def matrix_operators_worker_heartbeat(request: Request, worker_id: str) -> Response:
    return await _proxy_request(
        request=request,
        target_path=f"/internal/operators/workers/{worker_id}/heartbeat",
    )


@router.post("/operators/runs")
async def matrix_operators_runs_create(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/internal/operators/runs")


@router.get("/operators/runs")
async def matrix_operators_runs(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/internal/operators/runs")


@router.get("/audit/logs")
async def matrix_audit_logs(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/audit/logs")


@router.post("/transcribe")
async def matrix_transcribe(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/transcribe", method="POST")


@router.post("/upload")
async def matrix_upload(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/upload", method="POST")


@router.post("/search")
async def matrix_search(request: Request) -> Response:
    return await _proxy_request(request=request, target_path="/search", method="POST")
