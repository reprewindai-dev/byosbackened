from core.security.zero_trust import _PUBLIC_PATHS
from license.middleware import LICENSE_EXEMPT_PATHS


def test_status_data_is_license_exempt():
    assert "/status/data" in LICENSE_EXEMPT_PATHS


def test_status_data_is_public_zero_trust_path():
    assert "/status/data" in _PUBLIC_PATHS
