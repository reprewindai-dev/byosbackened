from license.middleware import LICENSE_EXEMPT_PATHS


def test_status_data_is_license_exempt():
    assert "/status/data" in LICENSE_EXEMPT_PATHS
