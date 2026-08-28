from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/provider/r4-411b-google-routes-live-validation-v1.json"


def load() -> dict[str, Any]:
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Google Routes contract must be an object")
    return payload


def canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


EXPECTED_DIGEST: str | None = None


def validate(payload: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    if (
        payload.get("schemaVersion") != 1
        or payload.get("contractId") != "r4-411b-google-routes-live-validation-v1"
    ):
        findings.append("identity")
    if payload.get("taskId") != "R4-411B" or payload.get("status") != "HUMAN_GATE_PENDING":
        findings.append("status")
    provider = payload.get("provider", {})
    if provider != {
        "name": "GOOGLE_MAPS_PLATFORM",
        "product": "GOOGLE_MAPS_ROUTES_API",
        "operations": ["ComputeRoutes", "ComputeRouteMatrix"],
        "endpointRegion": "GOOGLE_MANAGED_NOT_TOKYO_PINNED",
        "validated": False,
    }:
        findings.append("provider")
    prerequisites = payload.get("prerequisites", {})
    if prerequisites != {
        "googleCloudProject": "CREATED",
        "billing": "ENABLED",
        "routesApi": "ENABLED",
        "apiKey": "CREATED_AND_LOCALLY_CONFIGURED",
        "japanRoutingCoverage": "DOCUMENTED_SUPPORTED",
        "japanMatrixEntitlement": "NOT_ASSERTED",
    }:
        findings.append("prerequisites")
    secret = payload.get("secretInjection", {})
    if (
        secret.get("environmentVariable") != "ROUTEMIND_GOOGLE_ROUTES_API_KEY"
        or secret.get("presenceCheck") != "SET_OR_MISSING_ONLY"
        or secret.get("source") not in {"external_secret_store_or_process_environment"}
        or set(secret.get("forbiddenDestinations", []))
        != {
            "git",
            "history",
            "evidence",
            "logs",
            "snapshots",
            "ci_output",
            "frontend_bundle",
        }
    ):
        findings.append("secret_injection")
    fixture = payload.get("fixture", {})
    if (
        fixture.get("scope") != "synthetic_tokyo_coordinates_only"
        or fixture.get("realPeopleOrBusinesses") is not False
        or fixture.get("durableBusinessIdentifiers") is not False
    ):
        findings.append("fixture")
    request = payload.get("requestContract", {})
    if set(request.get("outboundForbidden", [])) != {
        "tenant_id",
        "customer_id",
        "courier_id",
        "merchant_id",
        "order_id",
        "phone",
        "email",
        "name",
        "textual_private_address",
        "durable_domain_serialization",
    }:
        findings.append("privacy")
    bounded = payload.get("boundedLiveValidation", {})
    if bounded != {
        "authorized": False,
        "maximumPointRequests": 20,
        "maximumMatrixRequests": 5,
        "maximumMatrixElements": 100,
        "maximumDurationMinutes": 30,
        "maximumSpendUsdCents": 100,
        "newExecutionApprovalRequired": True,
        "accountOrResourceCreationAuthorized": False,
    }:
        findings.append("budget")
    claims = payload.get("claims", {})
    if claims != {
        "providerSelected": False,
        "providerLiveValidated": False,
        "productionReady": False,
        "japanMatrixEntitlement": False,
        "realCallsExecuted": False,
    }:
        findings.append("claims")
    gate = payload.get("humanGate", {})
    if gate.get("approvalDoesNotAuthorizeLiveCalls") is not True:
        findings.append("human_gate")
    if len(payload.get("evidenceContract", [])) < 8:
        findings.append("evidence_contract")
    return sorted(set(findings))


def main() -> int:
    payload = load()
    findings = validate(payload)
    if findings:
        for finding in findings:
            print(f"ERROR: google_routes:{finding}")
        return 1
    print(
        json.dumps(
            {
                "valid": True,
                "contractId": payload["contractId"],
                "canonicalSha256": canonical_digest(payload),
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
