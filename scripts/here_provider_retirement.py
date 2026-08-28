"""Validate the irreversible control-plane decision to retire HERE.

This gate deliberately audits historical HERE contracts without treating them as
active credentials or live-validation authorization.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/provider/r4-411-here-provider-retirement-v1.json"
GOOGLE_CONTRACT = ROOT / "contracts/provider/r4-411b-google-routes-live-validation-v1.json"
RETIREMENT_DIGEST = "0991151bdce71f5be2e725a21708efecf0184ba830903632e3584bfad74f3e3c"
GOOGLE_DIGEST = "a2d37bd79cc433e48fc76b5a1b4ba6518592bd5a1a8ac72bc38d1c000e3285d1"
HERE_LIVE_DIGEST = "4eacaad0c0d8a71a73715b750b370d58a4439d70b1f9dd1cc97d119599da6d1c"
HERE_CANDIDATE_DIGEST = "6d71059d2db366ce0ab3e54b7959f532346b0875101ebc1ab8da9189e8b3ac5c"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path.name} must contain a JSON object")
    return value


def digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_contract(payload: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    if payload.get("schemaVersion") != 1 or payload.get("contractId") != (
        "r4-411-here-provider-retirement-v1"
    ):
        findings.append("retirement:identity")
    if payload.get("taskId") != "R4-411" or payload.get("status") != "CLOSED_NOT_SELECTED":
        findings.append("retirement:terminal_status")
    if payload.get("provider") != "HERE_TECHNOLOGIES":
        findings.append("retirement:provider")
    decision = payload.get("decision", {})
    expected_decision = {
        "selection": "NOT_SELECTED",
        "retirement": "RETIRED",
        "replacement": "GOOGLE_MAPS_ROUTES",
        "salesApplication": "NOT_PURSUED",
        "matrixJapanAccess": "COMMERCIAL_ENTITLEMENT_REQUIRED",
        "liveValidation": "NOT_PERFORMED",
        "liveClaim": "NONE",
    }
    if decision != expected_decision:
        findings.append("retirement:decision")
    historical = payload.get("historicalContracts", [])
    expected_historical = [
        {
            "path": "contracts/provider/r4-410-travel-provider-human-gate-v2.json",
            "sha256": HERE_CANDIDATE_DIGEST,
        },
        {
            "path": "contracts/provider/r4-411-travel-provider-live-validation-v1.json",
            "sha256": HERE_LIVE_DIGEST,
        },
    ]
    if historical != expected_historical:
        findings.append("retirement:historical_contracts")
    active = payload.get("activeRuntime", {})
    if active != {
        "provider": "GOOGLE_MAPS_ROUTES",
        "primaryAdapter": "GoogleRoutesProvider",
        "fallbackAdapter": "LocalRoutingProvider",
        "hereCodeConfigDependencies": False,
        "hereSecretEnvironmentVariable": None,
        "liveCallsAuthorized": False,
        "productionClaim": False,
    }:
        findings.append("retirement:active_boundary")
    claims = payload.get("claims", {})
    if claims != {
        "hereProviderLiveValidated": False,
        "hereMatrixJapanEligible": False,
        "hereProductionSelected": False,
        "googleProviderLiveValidated": False,
    }:
        findings.append("retirement:claims")
    human_gate = payload.get("humanGate", {})
    if human_gate.get("requiredForRetirement") is not False or human_gate.get(
        "requiredForGoogleLiveValidation"
    ) is not True:
        findings.append("retirement:gate_boundary")
    if human_gate.get("googleContractSha256") != GOOGLE_DIGEST:
        findings.append("retirement:google_contract_binding")
    return findings


def validate_active_boundary() -> list[str]:
    findings: list[str] = []
    runtime = (ROOT / "services/compute-api/src/routemind_compute/api/runtime.py").read_text(
        encoding="utf-8"
    )
    if "GoogleRoutesProvider" not in runtime or "LocalRoutingProvider" not in runtime:
        findings.append("active:provider_composition")
    if "HERE" in runtime or "ROUTEMIND_TRAVEL_PROVIDER_API_KEY" in runtime:
        findings.append("active:here_runtime_residue")
    google = load(GOOGLE_CONTRACT)
    if digest(google) != GOOGLE_DIGEST:
        findings.append("active:google_contract_digest")
    return findings


def main() -> int:
    payload = load(CONTRACT)
    findings = validate_contract(payload) + validate_active_boundary()
    actual = digest(payload)
    if actual != RETIREMENT_DIGEST:
        findings.append("retirement:digest")
    if findings:
        for finding in findings:
            print(f"FAIL: {finding}")
        return 1
    print(f"PASS: HERE retirement contract {actual}")
    print(
        "PASS: historical contracts retained; active boundary is Google primary plus local fallback"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
