"""Tenant-safe, bounded telemetry volume attribution."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from threading import Lock

from prometheus_client import Counter

TENANT_KEY_HEADER = "X-RouteMind-Tenant-Key"
UNATTRIBUTED_KEY = "rtk_unattributed"
OVERFLOW_KEY = "rtk_overflow"
_TENANT_KEY = re.compile(r"^rtk_[0-9a-f]{24}$")

ATTRIBUTED_RECORDS = Counter(
    "routemind_telemetry_attributed_records_total",
    "Logical telemetry records attributed without exporting raw tenant identity.",
    ("service", "signal", "operation", "tenant_key"),
)


@dataclass(frozen=True)
class TelemetrySettings:
    max_active_tenant_keys: int = 64

    def __post_init__(self) -> None:
        if not 1 <= self.max_active_tenant_keys <= 256:
            raise ValueError("max_active_tenant_keys must be between 1 and 256")

    @classmethod
    def from_environment(cls) -> TelemetrySettings:
        raw = os.getenv("ROUTEMIND_TELEMETRY_MAX_TENANT_KEYS", "64")
        try:
            maximum = int(raw)
        except ValueError as error:
            raise ValueError("ROUTEMIND_TELEMETRY_MAX_TENANT_KEYS must be an integer") from error
        return cls(maximum)


class TenantTelemetryAttribution:
    """Admit a bounded set of already pseudonymized tenant keys."""

    def __init__(self, settings: TelemetrySettings | None = None) -> None:
        self.settings = settings or TelemetrySettings.from_environment()
        self._active: set[str] = set()
        self._lock = Lock()

    def resolve(self, carrier: Mapping[str, str]) -> str:
        normalized = {key.lower(): value for key, value in carrier.items()}
        candidate = normalized.get(TENANT_KEY_HEADER.lower(), "")
        if not _TENANT_KEY.fullmatch(candidate):
            return UNATTRIBUTED_KEY
        with self._lock:
            if candidate in self._active:
                return candidate
            if len(self._active) >= self.settings.max_active_tenant_keys:
                return OVERFLOW_KEY
            self._active.add(candidate)
            return candidate

    def record_http(self, tenant_key: str) -> None:
        for signal in ("trace", "metric"):
            ATTRIBUTED_RECORDS.labels("compute-api", signal, "http", tenant_key).inc()

    @property
    def active_key_count(self) -> int:
        with self._lock:
            return len(self._active)


__all__ = [
    "ATTRIBUTED_RECORDS",
    "OVERFLOW_KEY",
    "TENANT_KEY_HEADER",
    "UNATTRIBUTED_KEY",
    "TelemetrySettings",
    "TenantTelemetryAttribution",
]
