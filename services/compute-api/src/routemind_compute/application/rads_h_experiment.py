"""Fail-closed R3-342 RADS-H experiment support audit."""

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

_SCHEMA = "routemind-rads-h-experiment-v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CLAIM_BOUNDARY = "RADS_H_EXPERIMENT_DOES_NOT_ESTABLISH_SWITCHING_OR_SERVICE_EFFECT"
_ARMS = ("no_hysteresis", "fixed", "rads_baseline", "cooldown", "rads_h")
_METRICS = (
    "switching_rate",
    "dwell_ticks",
    "service_metric",
    "route_cost",
    "dispatch_latency",
    "instability",
    "recovery",
)
_SUPPORT_FIELDS = (
    "tick_level_strategy_sequence",
    "switch_events",
    "dwell_observations",
    "service_outcomes",
    "latency_observations",
    "recovery_windows",
)
_MISSING_METRIC_STATUS = "NOT_REPORTED_NO_SWITCH_LOGS"
_SOURCE_DIGESTS = {
    "baseline_plan": "a907a0a722e8782aa76277637fa92205cc10046e5aca85b2de81e555623016c3",
    "hysteresis_plan": "4b846bc8b971df269c1c6439b325ab61b7803a83812ced39b352f519acb929c5",
    "pilot_plan": "8880268766523069ad3db523a5babf2170eed47a34489d2850c89a46c76929be",
    "pilot_ledger": "d8c00899785cc9c9cfd7bd7eac1a25513d8131a1c992b60e106ba12709bc5d76",
    "pilot_analysis": "5c1c0963b3cb9d8809dd7d02355ef6f401ddd8c69b55dc1d6dc74c17a898a10c",
}

_STATUS = Literal["INSUFFICIENT_DATA", "READY_FOR_EXECUTION"]


class RadsHExperimentError(ValueError):
    """Raised when the R3-342 experiment plan or support audit is unsafe."""


@dataclass(frozen=True, slots=True)
class RadsHExperimentPlan:
    payload: Mapping[str, object]
    plan_digest: str
    manifest_sha256: str

    @property
    def experiment_id(self) -> str:
        return _text(self.payload, "experiment_id")


@dataclass(frozen=True, slots=True)
class RadsHSupportAudit:
    status: _STATUS
    plan_digest: str
    available_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]
    metric_status: tuple[tuple[str, str], ...]
    reason: str


def load_rads_h_experiment_plan(path: Path | str) -> RadsHExperimentPlan:
    """Load the R3-342 plan without running a material campaign."""

    plan_path = Path(path).expanduser().resolve()
    try:
        raw = plan_path.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RadsHExperimentError("RADS-H experiment plan is not valid UTF-8 JSON") from exc
    if not isinstance(parsed, Mapping):
        raise RadsHExperimentError("RADS-H experiment plan must be a JSON object")
    payload = dict(parsed)
    plan_digest = _text(payload, "plan_digest")
    unsigned = dict(payload)
    del unsigned["plan_digest"]
    if canonical_digest(unsigned) != plan_digest:
        raise RadsHExperimentError("RADS-H experiment plan digest does not match content")
    _validate(payload)
    return RadsHExperimentPlan(payload, plan_digest, sha256(raw).hexdigest())


def audit_rads_h_support(
    plan: RadsHExperimentPlan,
    artifact_support: Mapping[str, bool],
) -> RadsHSupportAudit:
    """Audit required tick-level support and refuse unsupported execution."""

    if set(artifact_support) != set(_SUPPORT_FIELDS):
        raise RadsHExperimentError("RADS-H artifact support fields mismatch")
    available = tuple(field for field in _SUPPORT_FIELDS if artifact_support[field])
    missing = tuple(field for field in _SUPPORT_FIELDS if not artifact_support[field])
    if missing:
        statuses = tuple((metric, _MISSING_METRIC_STATUS) for metric in _METRICS)
        return RadsHSupportAudit(
            "INSUFFICIENT_DATA",
            plan.plan_digest,
            available,
            missing,
            statuses,
            "R3-325 pair artifacts contain arm summaries but no required tick-level "
            "switching observations",
        )
    statuses = tuple((metric, "READY_FOR_EXECUTION") for metric in _METRICS)
    return RadsHSupportAudit(
        "READY_FOR_EXECUTION",
        plan.plan_digest,
        available,
        missing,
        statuses,
        "all preregistered R3-342 support fields are present",
    )


def _validate(value: Mapping[str, object]) -> None:
    required = {
        "schema_version",
        "task_id",
        "experiment_id",
        "baseline_reference",
        "hysteresis_reference",
        "frozen_at_utc",
        "question",
        "comparison_arms",
        "required_metrics",
        "thresholds",
        "support_requirements",
        "artifact_lineage",
        "execution_policy",
        "claim_boundary",
        "plan_digest",
    }
    if set(value) != required:
        raise RadsHExperimentError("RADS-H experiment plan fields mismatch")
    if _text(value, "schema_version") != _SCHEMA or _text(value, "task_id") != "R3-342":
        raise RadsHExperimentError("RADS-H experiment identity is unsupported")
    if _text(value, "experiment_id") != "r3-342-rads-h-v1":
        raise RadsHExperimentError("RADS-H experiment identifier is not frozen")
    if _text(value, "baseline_reference") != "RADS-BASELINE-v1":
        raise RadsHExperimentError("RADS-H baseline reference is not frozen")
    if _text(value, "hysteresis_reference") != "RADS-H-v1":
        raise RadsHExperimentError("RADS-H mechanism reference is not frozen")
    if _text(value, "claim_boundary") != _CLAIM_BOUNDARY:
        raise RadsHExperimentError("RADS-H experiment claim boundary is missing")
    _text(value, "frozen_at_utc")
    _text(value, "question")
    if (
        tuple(_text_mapping(item, "comparison arm") for item in _sequence(value, "comparison_arms"))
        != _ARMS
    ):
        raise RadsHExperimentError("RADS-H comparison arms are not frozen")
    if (
        tuple(_text_mapping(item, "metric") for item in _sequence(value, "required_metrics"))
        != _METRICS
    ):
        raise RadsHExperimentError("RADS-H required metrics are not frozen")
    _validate_thresholds(_mapping(value, "thresholds"))
    _validate_support(_mapping(value, "support_requirements"))
    _validate_lineage(_mapping(value, "artifact_lineage"))
    _validate_execution(_mapping(value, "execution_policy"))


def _validate_thresholds(value: Mapping[str, object]) -> None:
    _exact(
        value,
        {
            "switch_reduction_target",
            "service_noninferiority_margin",
            "route_cost_relative_bound",
            "holm_family_size",
        },
        "thresholds",
    )
    if _number(value, "switch_reduction_target") != 0.25:
        raise RadsHExperimentError("switching reduction target is not frozen")
    if _number(value, "service_noninferiority_margin") != -0.02:
        raise RadsHExperimentError("service noninferiority margin is not frozen")
    if (
        _number(value, "route_cost_relative_bound") != 0.03
        or _integer(value, "holm_family_size") != 16
    ):
        raise RadsHExperimentError("RADS-H statistical thresholds are not frozen")


def _validate_support(value: Mapping[str, object]) -> None:
    _exact(
        value,
        {"required_fields", "source_status", "reason", "synthetic_replay"},
        "support_requirements",
    )
    if (
        tuple(_text_mapping(item, "support field") for item in _sequence(value, "required_fields"))
        != _SUPPORT_FIELDS
    ):
        raise RadsHExperimentError("RADS-H support fields are not frozen")
    if _text(value, "source_status") != "INSUFFICIENT_DATA":
        raise RadsHExperimentError("RADS-H source support must remain INSUFFICIENT_DATA")
    if _bool(value, "synthetic_replay"):
        raise RadsHExperimentError("synthetic replay cannot substitute switching observations")
    _text(value, "reason")


def _validate_lineage(value: Mapping[str, object]) -> None:
    if set(value) != set(_SOURCE_DIGESTS):
        raise RadsHExperimentError("RADS-H artifact lineage fields mismatch")
    for key, expected in _SOURCE_DIGESTS.items():
        if _digest(value, key) != expected:
            raise RadsHExperimentError(f"RADS-H {key} digest does not match frozen lineage")


def _validate_execution(value: Mapping[str, object]) -> None:
    _exact(
        value,
        {
            "material_run_authorized",
            "r3_325_rerun",
            "write_external_artifacts",
            "resource_envelope",
        },
        "execution_policy",
    )
    if (
        _bool(value, "material_run_authorized")
        or _bool(value, "r3_325_rerun")
        or _bool(value, "write_external_artifacts")
    ):
        raise RadsHExperimentError("RADS-H execution policy must remain read-only")
    _text(value, "resource_envelope")


def _exact(value: Mapping[str, object], allowed: set[str], label: str) -> None:
    if set(value) != allowed:
        raise RadsHExperimentError(f"{label} fields mismatch")


def _mapping(value: Mapping[str, object], key: str) -> Mapping[str, object]:
    return _mapping_value(value.get(key), key)


def _mapping_value(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RadsHExperimentError(f"{label} must be an object")
    return value


def _sequence(value: Mapping[str, object], key: str) -> Sequence[object]:
    selected = value.get(key)
    if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes, bytearray)):
        raise RadsHExperimentError(f"{key} must be an array")
    return selected


def _text(value: Mapping[str, object], key: str) -> str:
    selected = value.get(key)
    if not isinstance(selected, str) or not selected.strip() or len(selected) > 1024:
        raise RadsHExperimentError(f"{key} must be non-empty text")
    return selected


def _text_mapping(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RadsHExperimentError(f"{label} must be non-empty text")
    return value


def _number(value: Mapping[str, object], key: str) -> float:
    selected = value.get(key)
    if (
        isinstance(selected, bool)
        or not isinstance(selected, (int, float))
        or not isfinite(selected)
    ):
        raise RadsHExperimentError(f"{key} must be a finite number")
    return float(selected)


def _integer(value: Mapping[str, object], key: str) -> int:
    selected = value.get(key)
    if isinstance(selected, bool) or not isinstance(selected, int):
        raise RadsHExperimentError(f"{key} must be an integer")
    return selected


def _bool(value: Mapping[str, object], key: str) -> bool:
    selected = value.get(key)
    if not isinstance(selected, bool):
        raise RadsHExperimentError(f"{key} must be boolean")
    return selected


def _digest(value: Mapping[str, object], key: str) -> str:
    selected = _text(value, key)
    if not _SHA256.fullmatch(selected):
        raise RadsHExperimentError(f"{key} must be a SHA-256 digest")
    return selected


__all__ = [
    "RadsHExperimentError",
    "RadsHExperimentPlan",
    "RadsHSupportAudit",
    "audit_rads_h_support",
    "load_rads_h_experiment_plan",
]
