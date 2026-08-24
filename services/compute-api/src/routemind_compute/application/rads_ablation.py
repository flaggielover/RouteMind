"""Fail-closed R3-348 preregistered RADS ablation support audit."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Literal

from routemind_compute.application.execution import canonical_digest

_SCHEMA = "routemind-rads-ablation-v1"
_CLAIM_BOUNDARY = "RADS_ABLATION_DOES_NOT_ESTABLISH_COMPONENT_IMPORTANCE_OR_EFFECT"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DIMENSIONS = (
    "risk",
    "adaptation",
    "hysteresis",
    "uncertainty",
    "counterfactual_feature",
    "threshold",
)
_APPLICABILITY = (
    "APPLICABLE_RADS_BASELINE",
    "APPLICABLE_RADS_H",
    "APPLICABLE_RADS_H",
    "APPLICABLE_SAFE_RADS",
    "NOT_APPLICABLE_FEATURE_ABSENT",
    "APPLICABLE_RADS_H_AND_SAFE_RADS",
)
_PHASES = (
    "CONFIRMATORY_PREREGISTERED",
    "CONFIRMATORY_PREREGISTERED",
    "CONFIRMATORY_PREREGISTERED",
    "CONFIRMATORY_DIAGNOSTIC",
    "PREREGISTERED_NOT_RUN",
    "CONFIRMATORY_SENSITIVITY",
)
_METRICS = (
    "assignment_rate",
    "route_cost",
    "service_metric",
    "switching_rate",
    "constraint_violation",
    "calibration_error",
    "fallback_rate",
    "dispatch_latency",
)
_SUPPORT = (
    "common_stream_identity",
    "decision_outcomes",
    "switching_observations",
    "constraint_outcomes",
    "uncertainty_calibration",
    "threshold_sensitivity_runs",
)
_SOURCE_DIGESTS = {
    "baseline_plan": "a907a0a722e8782aa76277637fa92205cc10046e5aca85b2de81e555623016c3",
    "hysteresis_experiment": "725bce8111db8652c6b52ef1c71e63429594aa4a329e0372e524471ea41ac967",
    "safe_rads_experiment": "182a3e6217f2c8e918049a4d55b78e340c8882a58e5dad106a7f738c3433783c",
    "pilot_plan": "8880268766523069ad3db523a5babf2170eed47a34489d2850c89a46c76929be",
    "pilot_ledger": "d8c00899785cc9c9cfd7bd7eac1a25513d8131a1c992b60e106ba12709bc5d76",
}


class RadsAblationError(ValueError):
    """Raised when the R3-348 plan or support input violates the frozen contract."""


@dataclass(frozen=True, slots=True)
class RadsAblationPlan:
    payload: Mapping[str, object]
    plan_digest: str
    manifest_sha256: str

    @property
    def experiment_id(self) -> str:
        return _text(self.payload, "experiment_id")


@dataclass(frozen=True, slots=True)
class RadsAblationAudit:
    status: Literal["INSUFFICIENT_DATA", "READY_FOR_EXECUTION"]
    plan_digest: str
    available_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]
    dimension_status: tuple[tuple[str, str], ...]
    metric_status: tuple[tuple[str, str], ...]
    reason: str


def load_rads_ablation_plan(path: Path | str) -> RadsAblationPlan:
    plan_path = Path(path).expanduser().resolve()
    try:
        raw = plan_path.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RadsAblationError("RADS ablation plan is not valid UTF-8 JSON") from exc
    if not isinstance(parsed, Mapping):
        raise RadsAblationError("RADS ablation plan must be a JSON object")
    payload = dict(parsed)
    digest = _text(payload, "plan_digest")
    unsigned = dict(payload)
    del unsigned["plan_digest"]
    if canonical_digest(unsigned) != digest:
        raise RadsAblationError("RADS ablation plan digest does not match content")
    _validate(payload)
    return RadsAblationPlan(payload, digest, sha256(raw).hexdigest())


def audit_rads_ablation_support(
    plan: RadsAblationPlan,
    artifact_support: Mapping[str, bool],
) -> RadsAblationAudit:
    if set(artifact_support) != set(_SUPPORT):
        raise RadsAblationError("RADS ablation support fields mismatch")
    available = tuple(field for field in _SUPPORT if artifact_support[field])
    missing = tuple(field for field in _SUPPORT if not artifact_support[field])
    not_applicable = "NOT_APPLICABLE_FEATURE_ABSENT"
    if missing:
        dimension_status = tuple(
            (
                dimension,
                not_applicable
                if dimension == "counterfactual_feature"
                else "NOT_EVALUATED_NO_ABLATION_LOGS",
            )
            for dimension in _DIMENSIONS
        )
        return RadsAblationAudit(
            "INSUFFICIENT_DATA",
            plan.plan_digest,
            available,
            missing,
            dimension_status,
            tuple((metric, "NOT_REPORTED_NO_ABLATION_LOGS") for metric in _METRICS),
            "R3-325 artifacts have aggregate arm summaries but no component-level "
            "ablation outcomes",
        )
    dimension_status = tuple(
        (
            dimension,
            not_applicable if dimension == "counterfactual_feature" else "READY_FOR_EXECUTION",
        )
        for dimension in _DIMENSIONS
    )
    return RadsAblationAudit(
        "READY_FOR_EXECUTION",
        plan.plan_digest,
        available,
        (),
        dimension_status,
        tuple((metric, "READY_FOR_EXECUTION") for metric in _METRICS),
        "all support for applicable preregistered ablations is present",
    )


def _validate(value: Mapping[str, object]) -> None:
    required = {
        "schema_version",
        "task_id",
        "experiment_id",
        "frozen_at_utc",
        "question",
        "ablations",
        "required_metrics",
        "analysis_plan",
        "support_requirements",
        "source_lineage",
        "execution_policy",
        "claim_boundary",
        "plan_digest",
    }
    if set(value) != required:
        raise RadsAblationError("RADS ablation plan fields mismatch")
    if _text(value, "schema_version") != _SCHEMA or _text(value, "task_id") != "R3-348":
        raise RadsAblationError("RADS ablation identity is unsupported")
    if _text(value, "experiment_id") != "r3-348-rads-ablation-v1":
        raise RadsAblationError("RADS ablation experiment identifier is not frozen")
    _text(value, "frozen_at_utc")
    _text(value, "question")
    if _text(value, "claim_boundary") != _CLAIM_BOUNDARY:
        raise RadsAblationError("RADS ablation claim boundary is missing")
    _validate_ablations(_sequence(value, "ablations"))
    metrics = tuple(_text_item(item, "metric") for item in _sequence(value, "required_metrics"))
    if metrics != _METRICS:
        raise RadsAblationError("RADS ablation metrics are not frozen")
    _validate_analysis(_mapping(value, "analysis_plan"))
    _validate_support(_mapping(value, "support_requirements"))
    _validate_lineage(_mapping(value, "source_lineage"))
    _validate_execution(_mapping(value, "execution_policy"))


def _validate_ablations(values: Sequence[object]) -> None:
    rows = tuple(_mapping_item(item, "ablation") for item in values)
    if tuple(_text(row, "dimension") for row in rows) != _DIMENSIONS:
        raise RadsAblationError("RADS ablation dimensions are not frozen")
    if tuple(_text(row, "applicability") for row in rows) != _APPLICABILITY:
        raise RadsAblationError("RADS ablation applicability is not frozen")
    if tuple(_text(row, "phase") for row in rows) != _PHASES:
        raise RadsAblationError("RADS ablation phase labels are not frozen")
    for row in rows:
        if set(row) != {"dimension", "intervention", "applicability", "phase", "support_field"}:
            raise RadsAblationError("RADS ablation row fields mismatch")
        _text(row, "intervention")
    support_fields = tuple(row["support_field"] for row in rows)
    if support_fields != (
        "decision_outcomes",
        "decision_outcomes",
        "switching_observations",
        "uncertainty_calibration",
        None,
        "threshold_sensitivity_runs",
    ):
        raise RadsAblationError("RADS ablation support mapping is not frozen")


def _validate_analysis(value: Mapping[str, object]) -> None:
    required = {
        "unit",
        "estimator",
        "confidence_level",
        "minimum_pairs",
        "multiplicity",
        "missing_support_outcome",
    }
    if set(value) != required:
        raise RadsAblationError("RADS ablation analysis fields mismatch")
    if (
        _text(value, "unit") != "paired_seed_regime_stream"
        or _text(value, "estimator") != "paired_difference_by_ablation_dimension"
        or _number(value, "confidence_level") != 0.95
        or _integer(value, "minimum_pairs") != 30
        or _text(value, "multiplicity") != "HOLM_ACROSS_APPLICABLE_DIMENSION_METRIC_FAMILY"
        or _text(value, "missing_support_outcome") != "INSUFFICIENT_DATA"
    ):
        raise RadsAblationError("RADS ablation analysis plan is not frozen")


def _validate_support(value: Mapping[str, object]) -> None:
    if set(value) != {"required_fields", "source_status", "synthetic_substitution", "reason"}:
        raise RadsAblationError("RADS ablation support requirements fields mismatch")
    fields = tuple(
        _text_item(item, "support field") for item in _sequence(value, "required_fields")
    )
    if fields != _SUPPORT:
        raise RadsAblationError("RADS ablation support fields are not frozen")
    if _text(value, "source_status") != "INSUFFICIENT_DATA" or _bool(
        value, "synthetic_substitution"
    ):
        raise RadsAblationError("RADS ablation support must remain fail-closed")
    _text(value, "reason")


def _validate_lineage(value: Mapping[str, object]) -> None:
    if set(value) != set(_SOURCE_DIGESTS):
        raise RadsAblationError("RADS ablation lineage fields mismatch")
    for key, expected in _SOURCE_DIGESTS.items():
        digest = _text(value, key)
        if digest != expected or not _SHA256.fullmatch(digest):
            raise RadsAblationError(f"RADS ablation {key} lineage is not frozen")


def _validate_execution(value: Mapping[str, object]) -> None:
    required = {
        "material_run_authorized",
        "r3_325_rerun",
        "write_external_artifacts",
        "post_result_removals",
        "manifest_changes",
        "resource_envelope",
    }
    if set(value) != required:
        raise RadsAblationError("RADS ablation execution fields mismatch")
    writes_or_runs = (
        _bool(value, "material_run_authorized")
        or _bool(value, "r3_325_rerun")
        or _bool(value, "write_external_artifacts")
    )
    if writes_or_runs:
        raise RadsAblationError("RADS ablation execution must remain read-only")
    if (
        _text(value, "post_result_removals") != "EXPLORATORY_ONLY"
        or _text(value, "manifest_changes") != "NEW_VERSION_REQUIRED"
    ):
        raise RadsAblationError("RADS ablation exploratory boundary is not frozen")
    _text(value, "resource_envelope")


def _mapping(value: Mapping[str, object], key: str) -> Mapping[str, object]:
    return _mapping_item(value.get(key), key)


def _mapping_item(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RadsAblationError(f"{label} must be an object")
    return value


def _sequence(value: Mapping[str, object], key: str) -> Sequence[object]:
    selected = value.get(key)
    if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes, bytearray)):
        raise RadsAblationError(f"{key} must be an array")
    return selected


def _text(value: Mapping[str, object], key: str) -> str:
    selected = value.get(key)
    if not isinstance(selected, str) or not selected.strip() or len(selected) > 1024:
        raise RadsAblationError(f"{key} must be non-empty text")
    return selected


def _text_item(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RadsAblationError(f"{label} must be non-empty text")
    return value


def _number(value: Mapping[str, object], key: str) -> float:
    selected = value.get(key)
    if isinstance(selected, bool) or not isinstance(selected, (int, float)):
        raise RadsAblationError(f"{key} must be numeric")
    return float(selected)


def _integer(value: Mapping[str, object], key: str) -> int:
    selected = value.get(key)
    if isinstance(selected, bool) or not isinstance(selected, int):
        raise RadsAblationError(f"{key} must be an integer")
    return selected


def _bool(value: Mapping[str, object], key: str) -> bool:
    selected = value.get(key)
    if not isinstance(selected, bool):
        raise RadsAblationError(f"{key} must be boolean")
    return selected


__all__ = [
    "RadsAblationAudit",
    "RadsAblationError",
    "RadsAblationPlan",
    "audit_rads_ablation_support",
    "load_rads_ablation_plan",
]
