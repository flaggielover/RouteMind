from __future__ import annotations

import pytest

from routemind_compute.application.telemetry import (
    OVERFLOW_KEY,
    TENANT_KEY_HEADER,
    UNATTRIBUTED_KEY,
    TelemetrySettings,
    TenantTelemetryAttribution,
)


def tenant_key(index: int) -> str:
    return f"rtk_{index:024x}"


def test_pseudonymous_tenant_keys_are_bounded_without_accepting_raw_identity() -> None:
    attribution = TenantTelemetryAttribution(TelemetrySettings(max_active_tenant_keys=2))

    assert attribution.resolve({"X-Tenant-Id": "raw-tenant"}) == UNATTRIBUTED_KEY
    assert attribution.resolve({TENANT_KEY_HEADER: "invalid"}) == UNATTRIBUTED_KEY
    assert attribution.resolve({TENANT_KEY_HEADER: tenant_key(1)}) == tenant_key(1)
    assert attribution.resolve({TENANT_KEY_HEADER.lower(): tenant_key(2)}) == tenant_key(2)
    assert attribution.resolve({TENANT_KEY_HEADER: tenant_key(1)}) == tenant_key(1)
    assert attribution.resolve({TENANT_KEY_HEADER: tenant_key(3)}) == OVERFLOW_KEY
    assert attribution.active_key_count == 2


def test_telemetry_settings_fail_closed_on_invalid_cardinality(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="between 1 and 256"):
        TelemetrySettings(max_active_tenant_keys=0)
    monkeypatch.setenv("ROUTEMIND_TELEMETRY_MAX_TENANT_KEYS", "many")
    with pytest.raises(ValueError, match="must be an integer"):
        TelemetrySettings.from_environment()
