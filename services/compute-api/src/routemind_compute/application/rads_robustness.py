"""Fail-closed R3-349 cross-regime RADS robustness support audit."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Literal

from routemind_compute.application.execution import canonical_digest

_SCHEMA = "routemind-rads-robustness-v1"
_CLAIM_BOUNDARY = "RADS_ROBUSTNESS_AUDIT_DOES_NOT_ESTABLISH_CROSS_REGIME_ROBUSTNESS"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_AXES = (
    "seeds",
    "demand",
    "supply",
    "merchant_delay",
    "traffic",
    "location_noise",
    "location_staleness",
    "compute_constraints",
)
_AXIS_SUPPORT = (
    "seed_stream_identity",
    "demand_regime",
    "supply_regime",
    "merchant_delay_regime",
    "traffic_regime",
    "location_noise_regime",
    "location_staleness_regime",
    "compute_constraint_regime",
)
_SOURCE_REGIMES = (
    ("pilot_replicates_0_through_7", "four_common_random_streams"),
    ("normal", "surge"),
    ("normal", "shortage"),
    ("normal", "merchant-delay"),
    ("normal", "travel-degradation"),
    ("UNSUPPORTED_NO_FROZEN_REGIME",),
    ("normal", "location-staleness"),
    ("normal", "compute-budget", "queue-pressure"),
)
_METRICS = (
    "assignment_rate",
    "route_cost",
    "service_metric",
    "switching_rate",
    "constraint_violation",
    "fallback_rate",
    "dispatch_latency",
)
_SUPPORT = (
    *_AXIS_SUPPORT,
    "paired_stream_identity",
    "rads_strategy_identity",
    "rads_outcomes",
)
_SOURCE_DIGESTS = {
    "statistical_protocol": "a6dae9d55641ff7966ef4a50cc00a63da3e936620c3c48f23cd2c2ce039375b5",
    "pilot_plan": "8880268766523069ad3db523a5babf2170eed47a34489d2850c89a46c76929be",
    "pilot_ledger": "d8c00899785cc9c9cfd7bd7eac1a25513d8131a1c992b60e106ba12709bc5d76",
    "pilot_analysis": "5c1c0963b3cb9d8809dd7d02355ef6f401ddd8c69b55dc1d6dc74c17a898a10c",
    "stability_map": "c6d7d4a5ac088570731e80a189c12cd79792256ac3669bdeed5f9049d6b4ee14",
    "ablation_plan": "c5644b75580db5d95f33a28ea6cd367906a235aac777f46890f862cdf952d2e7",
}
_MINIMUM_PAIRS = 30


class RadsRobustnessError(ValueError):
    """Raised when the robustness plan or support input violates the contract."""


@dataclass(frozen=True, slots=True)
class RadsRobustnessPlan:
    payload: Mapping[str, object]
    plan_digest: str
    manifest_sha256: str

    @property
    def study_id(self) -> str:
        return _text(self.payload, "study_id")


@dataclass(frozen=True, slots=True)
class RadsRobustnessAudit:
    status: Literal["INSUFFICIENT_DATA", "READY_FOR_CROSS_REGIME_ANALYSIS"]
    plan_digest: str
    available_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]
    axis_status: tuple[tuple[str, str], ...]
    axis_pair_counts: tuple[tuple[str, int], ...]
    metric_status: tuple[tuple[str, str], ...]
    broad_claim_status: str
    reason: str


def load_rads_robustness_plan(path: Path | str) -> RadsRobustnessPlan:
    plan_path = Path(path).expanduser().resolve()
    try:
        raw = plan_path.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RadsRobustnessError("RADS robustness plan is not valid UTF-8 JSON") from exc
    if not isinstance(parsed, Mapping):
        raise RadsRobustnessError("RADS robustness plan must be a JSON object")
    payload = dict(parsed)
    digest = _text(payload, "plan_digest")
    unsigned = dict(payload)
    del unsigned["plan_digest"]
    if canonical_digest(unsigned) != digest:
        raise RadsRobustnessError("RADS robustness plan digest does not match content")
    _validate(payload)
    return RadsRobustnessPlan(payload, digest, sha256(raw).hexdigest())


def audit_rads_robustness_support(
    plan: RadsRobustnessPlan,
    artifact_support: Mapping[str, bool],
    axis_pair_counts: Mapping[str, int],
) -> RadsRobustnessAudit:
    if set(artifact_support) != set(_SUPPORT):
        raise RadsRobustnessError("RADS robustness support fields mismatch")
    if set(axis_pair_counts) != set(_AXES):
        raise RadsRobustnessError("RADS robustness pair-count axes mismatch")
    if any(
        isinstance(count, bool) or not isinstance(count, int) or count < 0
        for count in axis_pair_counts.values()
    ):
        raise RadsRobustnessError("RADS robustness pair counts must be non-negative integers")

    available = tuple(field for field in _SUPPORT if artifact_support[field])
    missing = tuple(field for field in _SUPPORT if not artifact_support[field])
    has_rads_results = (
        artifact_support["rads_strategy_identity"] and artifact_support["rads_outcomes"]
    )
    axis_rows: list[tuple[str, str]] = []
    for axis, support_field in zip(_AXES, _AXIS_SUPPORT, strict=True):
        if not artifact_support[support_field]:
            disposition = "UNSUPPORTED_REGIME_NOT_PRESENT"
        elif not has_rads_results:
            disposition = "SOURCE_REGIME_PRESENT_NO_RADS_OUTCOME"
        elif axis_pair_counts[axis] < _MINIMUM_PAIRS:
            disposition = "INSUFFICIENT_PAIRS_FOR_AXIS"
        else:
            disposition = "READY_FOR_CROSS_REGIME_ANALYSIS"
        axis_rows.append((axis, disposition))

    pairing_ready = artifact_support["paired_stream_identity"]
    ready = (
        has_rads_results
        and pairing_ready
        and all(status == "READY_FOR_CROSS_REGIME_ANALYSIS" for _, status in axis_rows)
    )
    if ready:
        return RadsRobustnessAudit(
            "READY_FOR_CROSS_REGIME_ANALYSIS",
            plan.plan_digest,
            available,
            (),
            tuple(axis_rows),
            tuple((axis, axis_pair_counts[axis]) for axis in _AXES),
            tuple((metric, "READY_FOR_PREREGISTERED_ANALYSIS") for metric in _METRICS),
            "ELIGIBLE_ONLY_AFTER_ALL_PREREGISTERED_CROSS_REGIME_TESTS_PASS",
            "all axes, RADS outcomes, pairing identities, and minimum pair counts are present",
        )
    return RadsRobustnessAudit(
        "INSUFFICIENT_DATA",
        plan.plan_digest,
        available,
        missing,
        tuple(axis_rows),
        tuple((axis, axis_pair_counts[axis]) for axis in _AXES),
        tuple((metric, "NOT_REPORTED_NO_CROSS_REGIME_RADS_OUTCOMES") for metric in _METRICS),
        "PROHIBITED_NO_CROSS_REGIME_EVIDENCE",
        "source regimes do not provide complete, adequately powered cross-regime RADS outcomes",
    )


def _validate(value: Mapping[str, object]) -> None:
    required = {
        "schema_version",
        "task_id",
        "study_id",
        "frozen_at_utc",
        "question",
        "robustness_axes",
        "required_metrics",
        "analysis_plan",
        "support_requirements",
        "source_lineage",
        "execution_policy",
        "claim_boundary",
        "plan_digest",
    }
    if set(value) != required:
        raise RadsRobustnessError("RADS robustness plan fields mismatch")
    if _text(value, "schema_version") != _SCHEMA or _text(value, "task_id") != "R3-349":
        raise RadsRobustnessError("RADS robustness identity is unsupported")
    if _text(value, "study_id") != "r3-349-rads-robustness-v1":
        raise RadsRobustnessError("RADS robustness study identifier is not frozen")
    _text(value, "frozen_at_utc")
    _text(value, "question")
    if _text(value, "claim_boundary") != _CLAIM_BOUNDARY:
        raise RadsRobustnessError("RADS robustness claim boundary is missing")
    _validate_axes(_sequence(value, "robustness_axes"))
    metrics = tuple(_text_item(item, "metric") for item in _sequence(value, "required_metrics"))
    if metrics != _METRICS:
        raise RadsRobustnessError("RADS robustness metrics are not frozen")
    _validate_analysis(_mapping(value, "analysis_plan"))
    _validate_support(_mapping(value, "support_requirements"))
    _validate_lineage(_mapping(value, "source_lineage"))
    _validate_execution(_mapping(value, "execution_policy"))


def _validate_axes(values: Sequence[object]) -> None:
    rows = tuple(_mapping_item(item, "robustness axis") for item in values)
    if tuple(_text(row, "axis") for row in rows) != _AXES:
        raise RadsRobustnessError("RADS robustness axes are not frozen")
    if tuple(_text(row, "support_field") for row in rows) != _AXIS_SUPPORT:
        raise RadsRobustnessError("RADS robustness axis support is not frozen")
    regimes = tuple(
        tuple(_text_item(item, "source regime") for item in _sequence(row, "source_regimes"))
        for row in rows
    )
    if regimes != _SOURCE_REGIMES:
        raise RadsRobustnessError("RADS robustness source regimes are not frozen")
    if any(set(row) != {"axis", "source_regimes", "support_field"} for row in rows):
        raise RadsRobustnessError("RADS robustness axis fields mismatch")


def _validate_analysis(value: Mapping[str, object]) -> None:
    required = {
        "unit",
        "estimator",
        "confidence_level",
        "minimum_pairs_per_axis_level",
        "continuous_interval",
        "bootstrap_resamples",
        "multiplicity",
        "broad_claim_rule",
        "single_scenario_rule",
        "missing_support_outcome",
    }
    if set(value) != required:
        raise RadsRobustnessError("RADS robustness analysis fields mismatch")
    if (
        _text(value, "unit") != "paired_seed_regime_stream"
        or _text(value, "estimator") != "paired_difference_by_robustness_axis"
        or _number(value, "confidence_level") != 0.95
        or _integer(value, "minimum_pairs_per_axis_level") != _MINIMUM_PAIRS
        or _text(value, "continuous_interval") != "PAIRED_BOOTSTRAP_PERCENTILE"
        or _integer(value, "bootstrap_resamples") != 2000
        or _text(value, "multiplicity") != "HOLM_ACROSS_AXIS_METRIC_FAMILY"
        or _text(value, "broad_claim_rule")
        != "ALL_AXES_SUPPORTED_AND_ALL_PREREGISTERED_CROSS_REGIME_TESTS_PASS"
        or _text(value, "single_scenario_rule") != "NEVER_SUFFICIENT_FOR_BROAD_CLAIM"
        or _text(value, "missing_support_outcome") != "INSUFFICIENT_DATA"
    ):
        raise RadsRobustnessError("RADS robustness analysis plan is not frozen")


def _validate_support(value: Mapping[str, object]) -> None:
    if set(value) != {"required_fields", "source_status", "synthetic_substitution", "reason"}:
        raise RadsRobustnessError("RADS robustness support requirements fields mismatch")
    fields = tuple(
        _text_item(item, "support field") for item in _sequence(value, "required_fields")
    )
    if fields != _SUPPORT:
        raise RadsRobustnessError("RADS robustness support fields are not frozen")
    if _text(value, "source_status") != "INSUFFICIENT_DATA" or _bool(
        value, "synthetic_substitution"
    ):
        raise RadsRobustnessError("RADS robustness support must remain fail-closed")
    _text(value, "reason")


def _validate_lineage(value: Mapping[str, object]) -> None:
    if set(value) != set(_SOURCE_DIGESTS):
        raise RadsRobustnessError("RADS robustness lineage fields mismatch")
    for key, expected in _SOURCE_DIGESTS.items():
        digest = _text(value, key)
        if digest != expected or not _SHA256.fullmatch(digest):
            raise RadsRobustnessError(f"RADS robustness {key} lineage is not frozen")


def _validate_execution(value: Mapping[str, object]) -> None:
    required = {
        "material_run_authorized",
        "r3_325_rerun",
        "write_external_artifacts",
        "select_favorable_scenario",
        "synthetic_fill",
        "manifest_changes",
        "resource_envelope",
    }
    if set(value) != required:
        raise RadsRobustnessError("RADS robustness execution fields mismatch")
    prohibited = (
        _bool(value, "material_run_authorized")
        or _bool(value, "r3_325_rerun")
        or _bool(value, "write_external_artifacts")
        or _bool(value, "select_favorable_scenario")
        or _bool(value, "synthetic_fill")
    )
    if prohibited:
        raise RadsRobustnessError("RADS robustness execution must remain read-only and complete")
    if _text(value, "manifest_changes") != "NEW_VERSION_REQUIRED":
        raise RadsRobustnessError("RADS robustness manifest change policy is not frozen")
    _text(value, "resource_envelope")


def _mapping(value: Mapping[str, object], key: str) -> Mapping[str, object]:
    return _mapping_item(value.get(key), key)


def _mapping_item(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RadsRobustnessError(f"{label} must be an object")
    return value


def _sequence(value: Mapping[str, object], key: str) -> Sequence[object]:
    selected = value.get(key)
    if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes, bytearray)):
        raise RadsRobustnessError(f"{key} must be an array")
    return selected


def _text(value: Mapping[str, object], key: str) -> str:
    selected = value.get(key)
    if not isinstance(selected, str) or not selected.strip() or len(selected) > 1024:
        raise RadsRobustnessError(f"{key} must be non-empty text")
    return selected


def _text_item(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RadsRobustnessError(f"{label} must be non-empty text")
    return value


def _number(value: Mapping[str, object], key: str) -> float:
    selected = value.get(key)
    if isinstance(selected, bool) or not isinstance(selected, (int, float)):
        raise RadsRobustnessError(f"{key} must be numeric")
    return float(selected)


def _integer(value: Mapping[str, object], key: str) -> int:
    selected = value.get(key)
    if isinstance(selected, bool) or not isinstance(selected, int):
        raise RadsRobustnessError(f"{key} must be an integer")
    return selected


def _bool(value: Mapping[str, object], key: str) -> bool:
    selected = value.get(key)
    if not isinstance(selected, bool):
        raise RadsRobustnessError(f"{key} must be boolean")
    return selected


__all__ = [
    "RadsRobustnessAudit",
    "RadsRobustnessError",
    "RadsRobustnessPlan",
    "audit_rads_robustness_support",
    "load_rads_robustness_plan",
]
