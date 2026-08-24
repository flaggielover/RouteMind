"""Fail-closed R3-344 Safe-RADS constraint semantics plan loader."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from pathlib import Path

from routemind_compute.application.execution import canonical_digest

_SCHEMA = "routemind-safe-rads-formalization-v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CLAIM_BOUNDARY = "SAFE_RADS_FORMALIZATION_DOES_NOT_ESTABLISH_SAFETY_OR_EFFECT"
_SEMANTICS = ("hard", "chance", "risk", "penalty")
_SOURCE_DIGESTS = {
    "baseline_plan": "a907a0a722e8782aa76277637fa92205cc10046e5aca85b2de81e555623016c3",
    "rads_source": "d72caf93a53c9bc10ebdc4e0ebeecad13381c7cae4bb09531715bf385d29f22a",
}


class SafeRadsPlanError(ValueError):
    """Raised when Safe-RADS semantics are missing, ambiguous, or unsafe."""


@dataclass(frozen=True, slots=True)
class SafeRadsPlan:
    payload: Mapping[str, object]
    plan_digest: str
    manifest_sha256: str

    @property
    def mechanism_id(self) -> str:
        return _text(self.payload, "mechanism_id")


def load_safe_rads_plan(path: Path | str) -> SafeRadsPlan:
    """Load frozen Safe-RADS semantics without executing a policy or campaign."""

    manifest_path = Path(path).expanduser().resolve()
    try:
        raw = manifest_path.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SafeRadsPlanError("Safe-RADS plan is not valid UTF-8 JSON") from exc
    if not isinstance(parsed, Mapping):
        raise SafeRadsPlanError("Safe-RADS plan must be a JSON object")
    payload = dict(parsed)
    plan_digest = _text(payload, "plan_digest")
    unsigned = dict(payload)
    del unsigned["plan_digest"]
    if canonical_digest(unsigned) != plan_digest:
        raise SafeRadsPlanError("Safe-RADS plan digest does not match content")
    _validate(payload)
    return SafeRadsPlan(payload, plan_digest, sha256(raw).hexdigest())


def _validate(value: Mapping[str, object]) -> None:
    required = {
        "schema_version",
        "task_id",
        "mechanism_id",
        "baseline_reference",
        "frozen_at_utc",
        "question",
        "semantics",
        "primary_constraint",
        "uncertainty",
        "efficiency_cost",
        "fallback",
        "validation_authority",
        "execution_policy",
        "limitations",
        "source_lineage",
        "claim_boundary",
        "plan_digest",
    }
    if set(value) != required:
        raise SafeRadsPlanError("Safe-RADS plan fields mismatch")
    if _text(value, "schema_version") != _SCHEMA or _text(value, "task_id") != "R3-344":
        raise SafeRadsPlanError("Safe-RADS plan identity is unsupported")
    if _text(value, "mechanism_id") != "Safe-RADS-v1":
        raise SafeRadsPlanError("Safe-RADS mechanism identifier is not frozen")
    if _text(value, "baseline_reference") != "RADS-BASELINE-v1":
        raise SafeRadsPlanError("Safe-RADS baseline reference is not frozen")
    if _text(value, "claim_boundary") != _CLAIM_BOUNDARY:
        raise SafeRadsPlanError("Safe-RADS claim boundary is missing")
    _text(value, "frozen_at_utc")
    _text(value, "question")
    _validate_semantics(_mapping(value, "semantics"))
    _validate_constraint(_mapping(value, "primary_constraint"))
    _validate_uncertainty(_mapping(value, "uncertainty"))
    _validate_efficiency(_mapping(value, "efficiency_cost"))
    _validate_fallback(_mapping(value, "fallback"))
    _validate_authority(_mapping(value, "validation_authority"))
    _validate_execution(_mapping(value, "execution_policy"))
    _validate_limitations(_sequence(value, "limitations"))
    _validate_lineage(_mapping(value, "source_lineage"))


def _validate_semantics(value: Mapping[str, object]) -> None:
    _exact(value, set(_SEMANTICS), "semantics")
    expected = {
        "hard": "deterministic bound; a violating candidate is infeasible and cannot be committed",
        "chance": "probability of violation is at most epsilon under a declared uncertainty model",
        "risk": "expected, quantile, or tail-risk functional used as a measured "
        "constraint quantity",
        "penalty": "objective weight that trades cost against risk and cannot establish safety",
    }
    if any(_text(value, key) != expected[key] for key in expected):
        raise SafeRadsPlanError("Safe-RADS semantic distinction is not frozen")


def _validate_constraint(value: Mapping[str, object]) -> None:
    _exact(
        value, {"metric", "operator", "bound", "epsilon", "direction", "unit"}, "primary_constraint"
    )
    if _text(value, "metric") != "late_service_probability":
        raise SafeRadsPlanError("Safe-RADS primary metric is not frozen")
    if _text(value, "operator") != "less_than_or_equal":
        raise SafeRadsPlanError("Safe-RADS constraint operator is not frozen")
    if _number(value, "bound") != 0.05 or _number(value, "epsilon") != 0.05:
        raise SafeRadsPlanError("Safe-RADS epsilon or bound is not frozen")
    if _text(value, "direction") != "lower_is_safer" or _text(value, "unit") != "probability":
        raise SafeRadsPlanError("Safe-RADS constraint direction or unit is not frozen")


def _validate_uncertainty(value: Mapping[str, object]) -> None:
    _exact(
        value,
        {"model", "confidence_level", "minimum_observations", "calibration_required"},
        "uncertainty",
    )
    if _text(value, "model") != "one_sided_wilson_upper_bound":
        raise SafeRadsPlanError("Safe-RADS uncertainty model is not frozen")
    if _number(value, "confidence_level") != 0.95 or _integer(value, "minimum_observations") != 100:
        raise SafeRadsPlanError("Safe-RADS uncertainty thresholds are not frozen")
    if not _bool(value, "calibration_required"):
        raise SafeRadsPlanError("Safe-RADS calibration must be required")


def _validate_efficiency(value: Mapping[str, object]) -> None:
    _exact(value, {"metric", "relative_bound", "accounting_rule"}, "efficiency_cost")
    if _text(value, "metric") != "route_cost" or _number(value, "relative_bound") != 0.03:
        raise SafeRadsPlanError("Safe-RADS efficiency bound is not frozen")
    if _text(value, "accounting_rule") != "report_cost_of_feasibility_separately_from_safety":
        raise SafeRadsPlanError("Safe-RADS efficiency accounting is not frozen")


def _validate_fallback(value: Mapping[str, object]) -> None:
    _exact(
        value, {"on_hard_violation", "on_uncertainty_failure", "penalty_only_allowed"}, "fallback"
    )
    if _text(value, "on_hard_violation") != "reject_or_verified_safe_fallback":
        raise SafeRadsPlanError("Safe-RADS hard-violation fallback is not frozen")
    if _text(value, "on_uncertainty_failure") != "reject_candidate_and_emit_no_claim":
        raise SafeRadsPlanError("Safe-RADS uncertainty fallback is not frozen")
    if _bool(value, "penalty_only_allowed"):
        raise SafeRadsPlanError("penalty-only variant cannot claim safety")


def _validate_authority(value: Mapping[str, object]) -> None:
    _exact(value, {"proposal_owner", "durable_enforcer", "claim_boundary"}, "validation_authority")
    if _text(value, "proposal_owner") != "Python compute proposal boundary":
        raise SafeRadsPlanError("Safe-RADS proposal ownership is not frozen")
    if _text(value, "durable_enforcer") != "Java durable assignment boundary":
        raise SafeRadsPlanError("Safe-RADS durable authority is not frozen")
    if (
        _text(value, "claim_boundary")
        != "Java verifies hard constraints before commit; Python never owns durable correctness"
    ):
        raise SafeRadsPlanError("Safe-RADS authority claim boundary is not frozen")


def _validate_execution(value: Mapping[str, object]) -> None:
    _exact(
        value,
        {
            "material_run_authorized",
            "write_external_artifacts",
            "penalty_only_claims",
            "resource_envelope",
        },
        "execution_policy",
    )
    if (
        _bool(value, "material_run_authorized")
        or _bool(value, "write_external_artifacts")
        or _bool(value, "penalty_only_claims")
    ):
        raise SafeRadsPlanError("Safe-RADS execution policy must remain preregistration-only")
    _text(value, "resource_envelope")


def _validate_limitations(value: Sequence[object]) -> None:
    if not value or any(not isinstance(item, str) or not item.strip() for item in value):
        raise SafeRadsPlanError("Safe-RADS limitations must be non-empty text")


def _validate_lineage(value: Mapping[str, object]) -> None:
    if set(value) != set(_SOURCE_DIGESTS):
        raise SafeRadsPlanError("Safe-RADS source lineage fields mismatch")
    for key, expected in _SOURCE_DIGESTS.items():
        if _text(value, key) != expected or not _SHA256.fullmatch(_text(value, key)):
            raise SafeRadsPlanError(f"Safe-RADS {key} digest does not match frozen lineage")


def _exact(value: Mapping[str, object], allowed: set[str], label: str) -> None:
    if set(value) != allowed:
        raise SafeRadsPlanError(f"{label} fields mismatch")


def _mapping(value: Mapping[str, object], key: str) -> Mapping[str, object]:
    selected = value.get(key)
    if not isinstance(selected, Mapping):
        raise SafeRadsPlanError(f"{key} must be an object")
    return selected


def _sequence(value: Mapping[str, object], key: str) -> Sequence[object]:
    selected = value.get(key)
    if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes, bytearray)):
        raise SafeRadsPlanError(f"{key} must be an array")
    return selected


def _text(value: Mapping[str, object], key: str) -> str:
    selected = value.get(key)
    if not isinstance(selected, str) or not selected.strip() or len(selected) > 1024:
        raise SafeRadsPlanError(f"{key} must be non-empty text")
    return selected


def _number(value: Mapping[str, object], key: str) -> float:
    selected = value.get(key)
    if (
        isinstance(selected, bool)
        or not isinstance(selected, (int, float))
        or not isfinite(selected)
    ):
        raise SafeRadsPlanError(f"{key} must be a finite number")
    return float(selected)


def _integer(value: Mapping[str, object], key: str) -> int:
    selected = value.get(key)
    if isinstance(selected, bool) or not isinstance(selected, int):
        raise SafeRadsPlanError(f"{key} must be an integer")
    return selected


def _bool(value: Mapping[str, object], key: str) -> bool:
    selected = value.get(key)
    if not isinstance(selected, bool):
        raise SafeRadsPlanError(f"{key} must be boolean")
    return selected


__all__ = ["SafeRadsPlan", "SafeRadsPlanError", "load_safe_rads_plan"]
