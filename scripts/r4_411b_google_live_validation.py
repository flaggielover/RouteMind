"""Bounded Google Routes live validation for R4-411B.

The runner performs no account or resource mutation. It keeps the API key in
process memory, never emits request headers, and writes only redacted evidence.
Point and matrix calls are intentionally independent so one failure cannot hide
the other result.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/provider/r4-411b-google-routes-live-validation-v1.json"
EVIDENCE_DIR = ROOT / "evidence/gates/R4-411B"
USAGE_LEDGER_PATH = EVIDENCE_DIR / "google-live-validation-usage.json"
CONTRACT_DIGEST = "a2d37bd79cc433e48fc76b5a1b4ba6518592bd5a1a8ac72bc38d1c000e3285d1"
API_KEY_ENV = "ROUTEMIND_GOOGLE_ROUTES_API_KEY"
POINT_ENDPOINT = "https://routes.googleapis.com/directions/v2:computeRoutes"
MATRIX_ENDPOINT = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
MAX_POINT_REQUESTS = 20
MAX_MATRIX_REQUESTS = 5
MAX_MATRIX_ELEMENTS = 100
MAX_DURATION_SECONDS = 30 * 60
MAX_SPEND_USD = 1.0


class ValidationAbort(RuntimeError):
    """Fail-closed validation abort with a stable, non-sensitive classification."""


def _load_contract() -> dict[str, Any]:
    value = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationAbort("contract_malformed")
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != CONTRACT_DIGEST:
        raise ValidationAbort("contract_digest_mismatch")
    if value.get("taskId") != "R4-411B" or value.get("status") != "HUMAN_GATE_PENDING":
        raise ValidationAbort("contract_status_mismatch")
    bounded = value.get("boundedLiveValidation", {})
    if bounded.get("maximumPointRequests") != MAX_POINT_REQUESTS:
        raise ValidationAbort("contract_point_budget_mismatch")
    if bounded.get("maximumMatrixRequests") != MAX_MATRIX_REQUESTS:
        raise ValidationAbort("contract_matrix_budget_mismatch")
    if bounded.get("maximumMatrixElements") != MAX_MATRIX_ELEMENTS:
        raise ValidationAbort("contract_element_budget_mismatch")
    if bounded.get("maximumDurationMinutes") != 30 or bounded.get("maximumSpendUsdCents") != 100:
        raise ValidationAbort("contract_ceiling_mismatch")
    return value


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class _Budget:
    def __init__(
        self,
        *,
        initial_point_requests: int = 0,
        initial_matrix_requests: int = 0,
        initial_matrix_elements: int = 0,
        usage_ledger_path: Path | None = None,
    ) -> None:
        self.started = time.monotonic()
        self.point_requests = initial_point_requests
        self.matrix_requests = initial_matrix_requests
        self.matrix_elements = initial_matrix_elements
        self.usage_ledger_path = usage_ledger_path

    def _persist(self) -> None:
        if self.usage_ledger_path is None:
            return
        self.usage_ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.usage_ledger_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "contract_sha256": CONTRACT_DIGEST,
                    "point_requests": self.point_requests,
                    "matrix_requests": self.matrix_requests,
                    "matrix_elements": self.matrix_elements,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def consume(self, operation: str, elements: int = 1) -> None:
        if time.monotonic() - self.started >= MAX_DURATION_SECONDS:
            raise ValidationAbort("time_budget_exceeded")
        if operation == "ComputeRoutes":
            if self.point_requests >= MAX_POINT_REQUESTS:
                raise ValidationAbort("point_request_budget_exceeded")
            self.point_requests += 1
            self._persist()
        elif operation == "ComputeRouteMatrix":
            if self.matrix_requests >= MAX_MATRIX_REQUESTS:
                raise ValidationAbort("matrix_request_budget_exceeded")
            if self.matrix_elements + elements > MAX_MATRIX_ELEMENTS:
                raise ValidationAbort("matrix_element_budget_exceeded")
            self.matrix_requests += 1
            self.matrix_elements += elements
            self._persist()
        else:
            raise ValidationAbort("unknown_operation")

    def snapshot(self) -> dict[str, int | float]:
        return {
            "point_requests": self.point_requests,
            "matrix_requests": self.matrix_requests,
            "matrix_elements": self.matrix_elements,
            "elapsed_seconds": round(time.monotonic() - self.started, 3),
        }


class _HttpsTransport:
    """Transport boundary; never logs headers or provider payloads."""

    def __call__(self, **kwargs: object) -> Any:
        endpoint = kwargs["endpoint"]
        headers = kwargs["headers"]
        body = kwargs["body"]
        timeout = kwargs["timeout_seconds"]
        if not isinstance(endpoint, str) or not isinstance(headers, dict):
            raise TypeError("transport_arguments_invalid")
        if not isinstance(body, dict) or not isinstance(timeout, (int, float)):
            raise TypeError("transport_arguments_invalid")
        request = Request(
            endpoint,
            data=json.dumps(body, separators=(",", ":"), ensure_ascii=True).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=float(timeout)) as response:
                status = int(response.status)
                raw = response.read()
                provider_request_id = response.headers.get("x-request-id") or response.headers.get(
                    "x-goog-request-id"
                )
        except HTTPError as error:
            status = int(error.code)
            raw = error.read()
            provider_request_id = error.headers.get("x-request-id") or error.headers.get(
                "x-goog-request-id"
            )
        except URLError as error:
            raise OSError("provider_transport_unavailable") from error
        payload: object
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            lines: list[object] = []
            for line in raw.decode("utf-8", errors="replace").splitlines():
                if line.strip():
                    try:
                        lines.append(json.loads(line))
                    except json.JSONDecodeError:
                        raise ValueError("provider_payload_malformed") from None
            payload = lines
        from routemind_compute.application.google_routes import GoogleRoutesResponse

        return GoogleRoutesResponse(status, payload, provider_request_id)


def _result_base(operation: str) -> dict[str, Any]:
    return {
        "operation": operation,
        "status": "NOT_ATTEMPTED",
        "classification": "not_attempted",
        "provider": "google-routes",
        "fallback_used": False,
        "provenance": {},
    }


def _provenance(result: Any) -> dict[str, str]:
    return {str(key): str(value) for key, value in result.provenance}


def _optional_round(value: Any, digits: int) -> float | None:
    return round(value, digits) if isinstance(value, (int, float)) else None


def _run_point(
    provider: Any, origin: Any, destination: Any, budget: _Budget
) -> dict[str, Any]:
    output = _result_base("ComputeRoutes")
    try:
        budget.consume("ComputeRoutes")
        result = provider.estimate(origin, destination)
    except ValidationAbort as error:
        output.update({"status": "ABORTED", "classification": str(error)})
        return output
    except Exception as error:  # provider boundary is classified without payloads
        output.update(
            {
                "status": "ERROR",
                "classification": str(getattr(error, "classification", "transport_error")),
                "error_type": error.__class__.__name__,
                "fallback_used": True,
                "fallback_reason": str(getattr(error, "classification", "transport_error")),
            }
        )
        return output
    if result.fallback_used:
        output.update(
            {
                "status": "FALLBACK",
                "classification": result.fallback_reason or "external_failure",
                "fallback_used": True,
                "fallback_provider": result.provider,
                "fallback_reason": result.fallback_reason or "external_failure",
                "fallback_seconds": round(result.seconds, 3),
                "fallback_distance_kilometres": (
                    round(result.distance_kilometres, 6)
                    if result.distance_kilometres is not None
                    else None
                ),
                "provenance": {"provider": result.provider, "fallback": "explicit"},
            }
        )
        return output
    output.update(
        {
            "status": "OK",
            "classification": "provider_success",
            "seconds": round(result.seconds, 3),
            "distance_kilometres": _optional_round(result.distance_kilometres, 6),
            "traffic_seconds": round(result.traffic_seconds, 3),
            "provenance": _provenance(result),
        }
    )
    return output


def _run_matrix(
    provider: Any,
    origins: tuple[Any, ...],
    destinations: tuple[Any, ...],
    budget: _Budget,
) -> dict[str, Any]:
    output = _result_base("ComputeRouteMatrix")
    try:
        budget.consume("ComputeRouteMatrix", len(origins) * len(destinations))
        result = provider.matrix(origins, destinations)
    except ValidationAbort as error:
        output.update({"status": "ABORTED", "classification": str(error)})
        return output
    except Exception as error:  # provider boundary is classified without payloads
        output.update(
            {
                "status": "ERROR",
                "classification": str(getattr(error, "classification", "transport_error")),
                "error_type": error.__class__.__name__,
                "fallback_used": True,
                "fallback_reason": str(getattr(error, "classification", "transport_error")),
            }
        )
        return output
    if result.fallback_used:
        output.update(
            {
                "status": "FALLBACK",
                "classification": result.fallback_reason or "external_failure",
                "fallback_used": True,
                "fallback_provider": result.provider,
                "fallback_reason": result.fallback_reason or "external_failure",
                "fallback_cells": len(result.values)
                * (len(result.values[0]) if result.values else 0),
                "provenance": {"provider": result.provider, "fallback": "explicit"},
            }
        )
        return output
    cells = []
    for row in result.values:
        cells.append(
            [
                {
                    "status": item.status,
                    "error_class": item.error_class,
                    "seconds": round(item.seconds, 3),
                    "distance_kilometres": _optional_round(item.distance_kilometres, 6),
                    "fallback_used": item.fallback_used,
                    "provenance": _provenance(item),
                }
                for item in row
            ]
        )
    cell_has_error = any(item["status"] == "ERROR" for row in cells for item in row)
    output.update(
        {
            "status": "PARTIAL" if cell_has_error else "OK",
            "classification": "partial_provider_response" if cell_has_error else "provider_success",
            "cells": cells,
            "provenance": {"provider": "google-maps-routes", "operation": "ComputeRouteMatrix"},
        }
    )
    return output


def _write_evidence(evidence: dict[str, Any], api_key: str) -> Path:
    serialized = json.dumps(evidence, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if api_key and api_key in serialized:
        raise ValidationAbort("secret_leakage_detected")
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = EVIDENCE_DIR / f"google-live-validation-{timestamp}.json"
    suffix = 1
    while path.exists():
        path = EVIDENCE_DIR / f"google-live-validation-{timestamp}-{suffix}.json"
        suffix += 1
    path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _load_usage_ledger() -> dict[str, int]:
    if not USAGE_LEDGER_PATH.exists():
        return {"point_requests": 0, "matrix_requests": 0, "matrix_elements": 0}
    try:
        value = json.loads(USAGE_LEDGER_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationAbort("usage_ledger_malformed") from error
    if not isinstance(value, dict) or value.get("contract_sha256") != CONTRACT_DIGEST:
        raise ValidationAbort("usage_ledger_contract_mismatch")
    counts: dict[str, int] = {}
    for field in ("point_requests", "matrix_requests", "matrix_elements"):
        raw = value.get(field, 0)
        if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
            raise ValidationAbort("usage_ledger_invalid_counts")
        counts[field] = raw
    if counts["point_requests"] > MAX_POINT_REQUESTS:
        raise ValidationAbort("point_request_budget_exceeded")
    if counts["matrix_requests"] > MAX_MATRIX_REQUESTS:
        raise ValidationAbort("matrix_request_budget_exceeded")
    if counts["matrix_elements"] > MAX_MATRIX_ELEMENTS:
        raise ValidationAbort("matrix_element_budget_exceeded")
    return counts


def main() -> int:
    try:
        _load_contract()
        api_key = os.environ.get(API_KEY_ENV, "")
        if not api_key.strip():
            raise ValidationAbort("missing_credentials")
        from routemind_compute.application.google_routes import (
            GoogleRoutesPolicy,
            GoogleRoutesProvider,
        )
        from routemind_compute.application.travel import (
            DeterministicLocalTravelProvider,
            FallbackTravelTimeProvider,
        )
        from routemind_compute.domain.dispatch import GeoPoint

        policy = GoogleRoutesPolicy(
            max_retries=0,
            max_point_requests=MAX_POINT_REQUESTS,
            max_matrix_requests=MAX_MATRIX_REQUESTS,
            max_matrix_elements=MAX_MATRIX_ELEMENTS,
            max_duration_seconds=MAX_DURATION_SECONDS,
            max_spend_usd=MAX_SPEND_USD,
            rate_limit_per_second=0,
        )
        provider = FallbackTravelTimeProvider(
            GoogleRoutesProvider(_HttpsTransport(), policy=policy),
            DeterministicLocalTravelProvider(),
            timeout_seconds=3.0,
        )
        tokyo_station = GeoPoint(35.681236, 139.767125)
        shinjuku = GeoPoint(35.689592, 139.700413)
        shibuya = GeoPoint(35.658034, 139.701636)
        prior_usage = _load_usage_ledger()
        budget = _Budget(
            initial_point_requests=prior_usage["point_requests"],
            initial_matrix_requests=prior_usage["matrix_requests"],
            initial_matrix_elements=prior_usage["matrix_elements"],
            usage_ledger_path=USAGE_LEDGER_PATH,
        )
        started_at = _now()
        point = _run_point(provider, tokyo_station, shinjuku, budget)
        matrix = _run_matrix(
            provider, (tokyo_station, shinjuku), (shinjuku, shibuya), budget
        )
        finished_at = _now()
        point_ok = point["status"] == "OK"
        matrix_ok = matrix["status"] == "OK"
        evidence = {
            "schema_version": 1,
            "task_id": "R4-411B",
            "contract_sha256": CONTRACT_DIGEST,
            "execution": {
                "started_at": started_at,
                "finished_at": finished_at,
                "point": point,
                "matrix": matrix,
                "provider": "GOOGLE_MAPS_PLATFORM",
                "region_claim": "GOOGLE_MANAGED_NOT_TOKYO_PINNED",
                "fixture": "committed_synthetic_fixture_v1 / Tokyo coordinates",
                "live_calls_authorized_by_owner": True,
                "api_key_presence": "SET",
                "prior_usage": prior_usage,
                "no_account_or_resource_mutation": True,
            },
            "budget": {
                **budget.snapshot(),
                "maximum_point_requests": MAX_POINT_REQUESTS,
                "maximum_matrix_requests": MAX_MATRIX_REQUESTS,
                "maximum_matrix_elements": MAX_MATRIX_ELEMENTS,
                "maximum_duration_seconds": MAX_DURATION_SECONDS,
                "maximum_spend_usd": MAX_SPEND_USD,
                "observed_external_cost_usd": "NOT_AVAILABLE_WITHOUT_BILLING_READBACK",
                "conservative_cost_upper_bound_usd": MAX_SPEND_USD,
            },
            "classification": {
                "compute_routes": "PASS" if point_ok else "FAIL",
                "compute_route_matrix": matrix["status"],
                "overall": (
                    "PASS"
                    if point_ok and matrix_ok
                    else "PARTIAL"
                    if (
                        point_ok
                        or matrix_ok
                        or point["status"] == "FALLBACK"
                        or matrix["status"] == "PARTIAL"
                    )
                    else "FAIL"
                ),
                "japan_matrix": "OBSERVED_PROVIDER_RESULT_ONLY; NO_ENTITLEMENT_CLAIM",
                "production_claim": False,
            },
            "privacy": {
                "synthetic_only": True,
                "forbidden_business_identifiers_sent": False,
                "secret_in_evidence": False,
                "secret_in_logs": False,
            },
        }
        path = _write_evidence(evidence, api_key)
        print(
            json.dumps(
                {
                    "status": "COMPLETE",
                    "evidence": str(path),
                    "classification": evidence["classification"],
                    "budget": evidence["budget"],
                },
                sort_keys=True,
            )
        )
        return 0
    except ValidationAbort as error:
        print(json.dumps({"status": "ABORTED", "classification": str(error)}, sort_keys=True))
        return 2
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "ABORTED",
                    "classification": "runner_error",
                    "error_type": error.__class__.__name__,
                },
                sort_keys=True,
            )
        )
        return 2


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "services/compute-api/src"))
    raise SystemExit(main())
