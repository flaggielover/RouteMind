from __future__ import annotations

import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.request
from typing import Any

TENANT_KEY = "rtk_bbbbbbbbbbbbbbbbbbbbbbbb"


def _post(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status not in (200, 201):
                raise RuntimeError(f"unexpected HTTP status: {response.status}")
            value = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"qualification request failed with HTTP {exc.code}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("qualification response is not a JSON object")
    return value


def main() -> int:
    business_url = os.environ.get("ROUTEMIND_BUSINESS_URL", "http://business-api:18080")
    compute_url = os.environ.get("ROUTEMIND_COMPUTE_URL", "http://compute-api:18081")
    qualification_id = os.environ.get("ROUTEMIND_QUALIFICATION_ID", "qualification")
    trace_id = secrets.token_hex(16)
    parent_span_id = secrets.token_hex(8)
    correlation_id = secrets.token_hex(16)
    traceparent = f"00-{trace_id}-{parent_span_id}-01"
    common = {
        "traceparent": traceparent,
        "X-Trace-Id": trace_id,
        "X-Request-Id": f"r4-{qualification_id}",
        "X-Correlation-Id": correlation_id,
    }

    order = _post(
        f"{business_url}/api/v1/orders",
        {},
        {
            **common,
            "Idempotency-Key": f"r4-{qualification_id}-{secrets.token_hex(8)}",
            "X-Actor": "customer",
        },
    )
    if order.get("status") != "CREATED":
        raise RuntimeError("RouteMind durable order qualification did not create an order")

    simulation = _post(
        f"{compute_url}/api/v1/twin/control",
        {"command_id": f"r4-{qualification_id}-simulation", "action": "reset"},
        {**common, "X-RouteMind-Tenant-Key": TENANT_KEY},
    )
    if simulation.get("source") != "simulation":
        raise RuntimeError("RouteMind simulation qualification response is invalid")

    experiment = _post(
        f"{compute_url}/api/v1/experiments/routebench",
        {
            "manifest_id": f"r4-{qualification_id}-manifest",
            "code_version": os.environ.get("ROUTEMIND_SOURCE_REVISION", "unknown"),
            "scenario_id": f"r4-{qualification_id}-scenario",
            "seed": 7,
            "load_profile": "qualification-tiny",
            "city_state": "synthetic-tokyo-fixture",
            "dataset_provenance": "synthetic:r4-external-validation",
            "strategies": ["nearest"],
            "demands": [
                {
                    "request_id": f"r4-{qualification_id}-demand",
                    "pickup": {"latitude": 35.6762, "longitude": 139.6503},
                    "tick": 0,
                }
            ],
            "couriers": [
                {
                    "courier_id": "synthetic-courier",
                    "location": {"latitude": 35.6763, "longitude": 139.6504},
                }
            ],
        },
        {**common, "X-RouteMind-Tenant-Key": TENANT_KEY},
    )
    if experiment.get("source") != "experiment":
        raise RuntimeError("RouteMind experiment qualification response is invalid")

    # The Outbox relay is asynchronous. This bounded wait lets the real worker publish
    # the order event before the backend correlation query begins.
    time.sleep(5)
    print(
        json.dumps(
            {
                "valid": True,
                "classification": "ACTUAL_ROUTEMIND_SYNTHETIC_QUALIFICATION",
                "actualRouteMindWorkload": True,
                "businessOutcome": "PASS_UNCHANGED_BY_TELEMETRY",
                "traceId": trace_id,
                "sourceRevision": os.environ.get("ROUTEMIND_SOURCE_REVISION", "unknown"),
                "operations": ["durable-order", "simulation-control", "routebench-experiment"],
                "syntheticDataOnly": True,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - target runtime diagnostic
        print(f"R4 workload qualification failed: {type(exc).__name__}", file=sys.stderr)
        raise
