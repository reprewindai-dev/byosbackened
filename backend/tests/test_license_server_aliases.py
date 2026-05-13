from license.server import app


def test_license_server_exposes_legacy_and_canonical_aliases():
    paths = {route.path for route in app.routes}

    assert "/issue" in paths
    assert "/verify" in paths
    assert "/api/licenses/issue" in paths
    assert "/api/licenses/verify" in paths
