"""Fail-closed R3-345 Safe-RADS experiment support audit."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from pathlib import Path
from typing import Literal

from routemind_compute.application.execution import canonical_digest

_SCHEMA = "routemind-safe-rads-experiment-v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CLAIM_BOUNDARY = "SAFE_RADS_EXPERIMENT_DOES_NOT_ESTABLISH_SAFETY_OR_EFFECT"
_ARMS = ("unconstrained", "fixed", "penalty_only", "conservative")
_METRICS = (
    "constraint_violation",
    "feasibility",
    "route_cost",
    "lateness",
    "calibration",
    "fallback_rate",
    "tightness_sensitivity",
)
_SUPPORT = (
    "violation_events",
    "feasibility_outcomes",
    "route_cost_observations",
    "lateness_observations",
    "calibration_records",
    "tightness_sensitivity_runs",
)
_SOURCE_DIGESTS = {
    "safe_rads_plan": "82fed4dc95bec7ccbfa10ead770d63e2de6f47bb081d0b5d05672382462f6644",
    "baseline_plan": "a907a0a722e8782aa76277637fa92205cc10046e5aca85b2de81e555623016c3",
    "pilot_plan": "8880268766523069ad3db523a5babf2170eed47a34489d2850c89a46c76929be",
    "pilot_ledger": "d8c00899785cc9c9cfd7bd7eac1a25513d8131a1c992b60e106ba12709bc5d76",
}


class SafeRadsExperimentError(ValueError):
    """Raised when a Safe-RADS experiment plan or audit input is unsafe."""


@dataclass(frozen=True, slots=True)
class SafeRadsExperimentPlan:
    payload: Mapping[str, object]
    plan_digest: str
    manifest_sha256: str

    @property
    def experiment_id(self) -> str:
        return _text(self.payload, "experiment_id")


@dataclass(frozen=True, slots=True)
class SafeRadsSupportAudit:
    status: Literal["INSUFFICIENT_DATA", "READY_FOR_EXECUTION"]
    plan_digest: str
    available_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]
    metric_status: tuple[tuple[str, str], ...]
    reason: str


def load_safe_rads_experiment_plan(path: Path | str) -> SafeRadsExperimentPlan:
    plan_path = Path(path).expanduser().resolve()
    try:
        raw = plan_path.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SafeRadsExperimentError("Safe-RADS experiment plan is not valid UTF-8 JSON") from exc
    if not isinstance(parsed, Mapping):
        raise SafeRadsExperimentError("Safe-RADS experiment plan must be a JSON object")
    payload = dict(parsed)
    digest = _text(payload, "plan_digest")
    unsigned = dict(payload)
    del unsigned["plan_digest"]
    if canonical_digest(unsigned) != digest:
        raise SafeRadsExperimentError("Safe-RADS experiment plan digest does not match content")
    _validate(payload)
    return SafeRadsExperimentPlan(payload, digest, sha256(raw).hexdigest())


def audit_safe_rads_support(
    plan: SafeRadsExperimentPlan,
    artifact_support: Mapping[str, bool],
) -> SafeRadsSupportAudit:
    if set(artifact_support) != set(_SUPPORT):
        raise SafeRadsExperimentError("Safe-RADS support fields mismatch")
    available = tuple(field for field in _SUPPORT if artifact_support[field])
    missing = tuple(field for field in _SUPPORT if not artifact_support[field])
    if missing:
        return SafeRadsSupportAudit(
            "INSUFFICIENT_DATA",
            plan.plan_digest,
            available,
            missing,
            tuple((metric, "NOT_REPORTED_NO_SAFE_OUTCOMES") for metric in _METRICS),
            "R3-325 pair artifacts contain arm summaries but no Safe-RADS constraint outcomes",
        )
    return SafeRadsSupportAudit(
        "READY_FOR_EXECUTION",
        plan.plan_digest,
        available,
        missing,
        tuple((metric, "READY_FOR_EXECUTION") for metric in _METRICS),
        "all preregistered Safe-RADS support fields are present",
    )


def _validate(value: Mapping[str, object]) -> None:
    required = {
        "schema_version",
        "task_id",
        "experiment_id",
        "safe_rads_reference",
        "baseline_reference",
        "frozen_at_utc",
        "question",
        "comparison_arms",
        "required_metrics",
        "support_requirements",
        "thresholds",
        "artifact_lineage",
        "execution_policy",
        "claim_boundary",
        "plan_digest",
    }
    if set(value) != required:
        raise SafeRadsExperimentError("Safe-RADS experiment plan fields mismatch")
    if _text(value, "schema_version") != _SCHEMA or _text(value, "task_id") != "R3-345":
        raise SafeRadsExperimentError("Safe-RADS experiment identity is unsupported")
    if _text(value, "experiment_id") != "r3-345-safe-rads-v1":
        raise SafeRadsExperimentError("Safe-RADS experiment identifier is not frozen")
    if (
        _text(value, "safe_rads_reference") != "Safe-RADS-v1"
        or _text(value, "baseline_reference") != "RADS-BASELINE-v1"
    ):
        raise SafeRadsExperimentError("Safe-RADS references are not frozen")
    if _text(value, "claim_boundary") != _CLAIM_BOUNDARY:
        raise SafeRadsExperimentError("Safe-RADS experiment claim boundary is missing")
    _text(value, "frozen_at_utc")
    _text(value, "question")
    if tuple(_text_item(item, "arm") for item in _sequence(value, "comparison_arms")) != _ARMS:
        raise SafeRadsExperimentError("Safe-RADS experiment arms are not frozen")
    if (
        tuple(_text_item(item, "metric") for item in _sequence(value, "required_metrics"))
        != _METRICS
    ):
        raise SafeRadsExperimentError("Safe-RADS experiment metrics are not frozen")
    _validate_support(_mapping(value, "support_requirements"))
    _validate_thresholds(_mapping(value, "thresholds"))
    _validate_lineage(_mapping(value, "artifact_lineage"))
    _validate_execution(_mapping(value, "execution_policy"))


def _validate_support(value: Mapping[str, object]) -> None:
    if set(value) != {"required_fields", "source_status", "synthetic_replay", "reason"}:
        raise SafeRadsExperimentError("support requirements fields mismatch")
    if (
        tuple(_text_item(item, "support field") for item in _sequence(value, "required_fields"))
        != _SUPPORT
    ):
        raise SafeRadsExperimentError("Safe-RADS support fields are not frozen")
    if _text(value, "source_status") != "INSUFFICIENT_DATA" or _bool(value, "synthetic_replay"):
        raise SafeRadsExperimentError("Safe-RADS support must remain read-only and no-data")
    _text(value, "reason")


def _validate_thresholds(value: Mapping[str, object]) -> None:
    if set(value) != {
        "violation_bound",
        "confidence_level",
        "minimum_observations",
        "route_cost_relative_bound",
    }:
        raise SafeRadsExperimentError("Safe-RADS experiment thresholds fields mismatch")
    if _number(value, "violation_bound") != 0.05 or _number(value, "confidence_level") != 0.95:
        raise SafeRadsExperimentError("Safe-RADS experiment bounds are not frozen")
    if (
        _integer(value, "minimum_observations") != 100
        or _number(value, "route_cost_relative_bound") != 0.03
    ):
        raise SafeRadsExperimentError("Safe-RADS experiment thresholds are not frozen")


def _validate_lineage(value: Mapping[str, object]) -> None:
    if set(value) != set(_SOURCE_DIGESTS):
        raise SafeRadsExperimentError("Safe-RADS experiment lineage fields mismatch")
    for key, expected in _SOURCE_DIGESTS.items():
        digest = _text(value, key)
        if digest != expected or not _SHA256.fullmatch(digest):
            raise SafeRadsExperimentError(f"Safe-RADS {key} digest does not match frozen lineage")


def _validate_execution(value: Mapping[str, object]) -> None:
    if set(value) != {
        "material_run_authorized",
        "r3_325_rerun",
        "write_external_artifacts",
        "resource_envelope",
    }:
        raise SafeRadsExperimentError("Safe-RADS execution policy fields mismatch")
    if (
        _bool(value, "material_run_authorized")
        or _bool(value, "r3_325_rerun")
        or _bool(value, "write_external_artifacts")
    ):
        raise SafeRadsExperimentError("Safe-RADS experiment policy must remain read-only")
    _text(value, "resource_envelope")


def _mapping(value: Mapping[str, object], key: str) -> Mapping[str, object]:
    selected = value.get(key)
    if not isinstance(selected, Mapping):
        raise SafeRadsExperimentError(f"{key} must be an object")
    return selected


def _sequence(value: Mapping[str, object], key: str) -> Sequence[object]:
    selected = value.get(key)
    if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes, bytearray)):
        raise SafeRadsExperimentError(f"{key} must be an array")
    return selected


def _text(value: Mapping[str, object], key: str) -> str:
    selected = value.get(key)
    if not isinstance(selected, str) or not selected.strip() or len(selected) > 1024:
        raise SafeRadsExperimentError(f"{key} must be non-empty text")
    return selected


def _text_item(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SafeRadsExperimentError(f"{label} must be non-empty text")
    return value


def _number(value: Mapping[str, object], key: str) -> float:
    selected = value.get(key)
    if (
        isinstance(selected, bool)
        or not isinstance(selected, (int, float))
        or not isfinite(selected)
    ):
        raise SafeRadsExperimentError(f"{key} must be a finite number")
    return float(selected)


def _integer(value: Mapping[str, object], key: str) -> int:
    selected = value.get(key)
    if isinstance(selected, bool) or not isinstance(selected, int):
        raise SafeRadsExperimentError(f"{key} must be an integer")
    return selected


def _bool(value: Mapping[str, object], key: str) -> bool:
    selected = value.get(key)
    if not isinstance(selected, bool):
        raise SafeRadsExperimentError(f"{key} must be boolean")
    return selected


__all__ = [
    "SafeRadsExperimentError",
    "SafeRadsExperimentPlan",
    "SafeRadsSupportAudit",
    "audit_safe_rads_support",
    "load_safe_rads_experiment_plan",
]
