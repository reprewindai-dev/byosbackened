from types import SimpleNamespace

from apps.api.middleware.entitlement_check import EntitlementCheckMiddleware


def test_admin_and_owner_are_treated_as_enterprise():
    middleware = EntitlementCheckMiddleware(app=SimpleNamespace())

    admin_request = SimpleNamespace(state=SimpleNamespace(is_superuser=False, role="admin"))
    owner_request = SimpleNamespace(state=SimpleNamespace(is_superuser=False, role="owner"))
    superuser_request = SimpleNamespace(state=SimpleNamespace(is_superuser=True, role="user"))

    assert middleware._resolve_current_plan(admin_request, "workspace-1") == "enterprise"
    assert middleware._resolve_current_plan(owner_request, "workspace-1") == "enterprise"
    assert middleware._resolve_current_plan(superuser_request, "workspace-1") == "enterprise"
