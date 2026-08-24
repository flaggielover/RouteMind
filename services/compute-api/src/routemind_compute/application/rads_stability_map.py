"""Fail-closed R3-343 empirical RADS-H stability-map support audit."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Literal

from routemind_compute.application.execution import canonical_digest

_SCHEMA = "routemind-rads-stability-map-v1"
_CLAIM_BOUNDARY = "EMPIRICAL_STABILITY_MAP_DOES_NOT_ESTABLISH_THEORETICAL_STABILITY"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_AXES = (
    "relative_advantage",
    "dwell_ticks",
    "pressure_ticks",
    "regime_id",
    "strategy_pair",
)
_REPRESENTATIONS = (
    "below_exit, exit_band, below_enter, enter_pressure",
    "0, 1, 2, 3_or_more",
    "0, 1, 2_or_more",
    "observed_categorical",
    "observed_active_to_candidate",
)
_AXIS_SUPPORT = (
    "tick_state_observations",
    "tick_state_observations",
    "tick_state_observations",
    "regime_identity",
    "strategy_selections",
)
_METRICS = (
    "selection_rate",
    "switching_rate",
    "service_metric",
    "route_cost",
    "instability_rate",
)
_SUPPORT = (
    "tick_state_observations",
    "strategy_selections",
    "switch_events",
    "service_outcomes",
    "route_cost_outcomes",
    "instability_observations",
    "regime_identity",
    "pairing_unit",
)
_SOURCE_DIGESTS = {
    "hysteresis_plan": "4b846bc8b971df269c1c6439b325ab61b7803a83812ced39b352f519acb929c5",
    "hysteresis_experiment": "725bce8111db8652c6b52ef1c71e63429594aa4a329e0372e524471ea41ac967",
    "pilot_plan": "8880268766523069ad3db523a5babf2170eed47a34489d2850c89a46c76929be",
    "pilot_ledger": "d8c00899785cc9c9cfd7bd7eac1a25513d8131a1c992b60e106ba12709bc5d76",
}


class RadsStabilityMapError(ValueError):
    """Raised when the map plan or support input violates the frozen contract."""


@dataclass(frozen=True, slots=True)
class RadsStabilityMapPlan:
    payload: Mapping[str, object]
    plan_digest: str
    manifest_sha256: str

    @property
    def map_id(self) -> str:
        return _text(self.payload, "map_id")


@dataclass(frozen=True, slots=True)
class RadsStabilityMapAudit:
    status: Literal["INSUFFICIENT_DATA", "READY_FOR_MAPPING"]
    plan_digest: str
    available_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]
    axis_status: tuple[tuple[str, str], ...]
    metric_status: tuple[tuple[str, str], ...]
    coverage_status: str
    uncertainty_status: str
    reason: str
    interpretation: str = "EMPIRICAL_ONLY_NOT_THEORETICAL"


def load_rads_stability_map_plan(path: Path | str) -> RadsStabilityMapPlan:
    plan_path = Path(path).expanduser().resolve()
    try:
        raw = plan_path.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RadsStabilityMapError("RADS stability-map plan is not valid UTF-8 JSON") from exc
    if not isinstance(parsed, Mapping):
        raise RadsStabilityMapError("RADS stability-map plan must be a JSON object")
    payload = dict(parsed)
    digest = _text(payload, "plan_digest")
    unsigned = dict(payload)
    del unsigned["plan_digest"]
    if canonical_digest(unsigned) != digest:
        raise RadsStabilityMapError("RADS stability-map plan digest does not match content")
    _validate(payload)
    return RadsStabilityMapPlan(payload, digest, sha256(raw).hexdigest())


def audit_rads_stability_map_support(
    plan: RadsStabilityMapPlan,
    artifact_support: Mapping[str, bool],
) -> RadsStabilityMapAudit:
    if set(artifact_support) != set(_SUPPORT):
        raise RadsStabilityMapError("RADS stability-map support fields mismatch")
    available = tuple(field for field in _SUPPORT if artifact_support[field])
    missing = tuple(field for field in _SUPPORT if not artifact_support[field])
    if missing:
        return RadsStabilityMapAudit(
            "INSUFFICIENT_DATA",
            plan.plan_digest,
            available,
            missing,
            tuple((axis, "NOT_MAPPED_NO_TICK_LOGS") for axis in _AXES),
            tuple((metric, "NOT_REPORTED_NO_TICK_LOGS") for metric in _METRICS),
            "NO_ELIGIBLE_CELLS",
            "NOT_ESTIMATED_NO_CELL_SUPPORT",
            "R3-325 artifacts have aggregate arm summaries but no RADS-H state trajectories",
        )
    return RadsStabilityMapAudit(
        "READY_FOR_MAPPING",
        plan.plan_digest,
        available,
        (),
        tuple((axis, "READY_FOR_EMPIRICAL_MAPPING") for axis in _AXES),
        tuple((metric, "READY_FOR_EMPIRICAL_MAPPING") for metric in _METRICS),
        "READY_TO_COUNT_OBSERVED_AND_ELIGIBLE_CELLS",
        "READY_FOR_PREREGISTERED_INTERVALS",
        "all preregistered empirical stability-map support fields are present",
    )


def _validate(value: Mapping[str, object]) -> None:
    required = {
        "schema_version",
        "task_id",
        "map_id",
        "frozen_at_utc",
        "question",
        "state_axes",
        "map_metrics",
        "coverage_policy",
        "uncertainty_policy",
        "support_requirements",
        "source_lineage",
        "execution_policy",
        "claim_boundary",
        "plan_digest",
    }
    if set(value) != required:
        raise RadsStabilityMapError("RADS stability-map plan fields mismatch")
    if _text(value, "schema_version") != _SCHEMA or _text(value, "task_id") != "R3-343":
        raise RadsStabilityMapError("RADS stability-map identity is unsupported")
    if _text(value, "map_id") != "r3-343-empirical-stability-map-v1":
        raise RadsStabilityMapError("RADS stability-map identifier is not frozen")
    _text(value, "frozen_at_utc")
    _text(value, "question")
    if _text(value, "claim_boundary") != _CLAIM_BOUNDARY:
        raise RadsStabilityMapError("empirical/theoretical stability boundary is missing")
    _validate_axes(_sequence(value, "state_axes"))
    metrics = tuple(_text_item(item, "metric") for item in _sequence(value, "map_metrics"))
    if metrics != _METRICS:
        raise RadsStabilityMapError("RADS stability-map metrics are not frozen")
    _validate_coverage(_mapping(value, "coverage_policy"))
    _validate_uncertainty(_mapping(value, "uncertainty_policy"))
    _validate_support(_mapping(value, "support_requirements"))
    _validate_lineage(_mapping(value, "source_lineage"))
    _validate_execution(_mapping(value, "execution_policy"))


def _validate_axes(values: Sequence[object]) -> None:
    rows = tuple(_mapping_item(item, "state axis") for item in values)
    if tuple(_text(row, "axis") for row in rows) != _AXES:
        raise RadsStabilityMapError("RADS stability-map axes are not frozen")
    if tuple(_text(row, "representation") for row in rows) != _REPRESENTATIONS:
        raise RadsStabilityMapError("RADS stability-map axis representations are not frozen")
    if tuple(_text(row, "support_field") for row in rows) != _AXIS_SUPPORT:
        raise RadsStabilityMapError("RADS stability-map axis support is not frozen")
    if any(set(row) != {"axis", "representation", "support_field"} for row in rows):
        raise RadsStabilityMapError("RADS stability-map axis fields mismatch")


def _validate_coverage(value: Mapping[str, object]) -> None:
    if set(value) != {
        "minimum_cell_observations",
        "unobserved_cell_label",
        "underpowered_cell_label",
        "coverage_report",
    }:
        raise RadsStabilityMapError("stability-map coverage fields mismatch")
    if (
        _integer(value, "minimum_cell_observations") != 30
        or _text(value, "unobserved_cell_label") != "UNSUPPORTED_NO_OBSERVATIONS"
        or _text(value, "underpowered_cell_label") != "INSUFFICIENT_CELL_SUPPORT"
        or _text(value, "coverage_report") != "REQUIRED_OBSERVED_AND_ELIGIBLE_CELL_COUNTS"
    ):
        raise RadsStabilityMapError("stability-map coverage policy is not frozen")


def _validate_uncertainty(value: Mapping[str, object]) -> None:
    if set(value) != {
        "confidence_level",
        "proportion_interval",
        "continuous_interval",
        "bootstrap_resamples",
        "unit",
    }:
        raise RadsStabilityMapError("stability-map uncertainty fields mismatch")
    if (
        _number(value, "confidence_level") != 0.95
        or _text(value, "proportion_interval") != "WILSON"
        or _text(value, "continuous_interval") != "PAIRED_BOOTSTRAP_PERCENTILE"
        or _integer(value, "bootstrap_resamples") != 2000
        or _text(value, "unit") != "paired_seed_regime_stream"
    ):
        raise RadsStabilityMapError("stability-map uncertainty policy is not frozen")


def _validate_support(value: Mapping[str, object]) -> None:
    if set(value) != {"required_fields", "source_status", "synthetic_substitution", "reason"}:
        raise RadsStabilityMapError("stability-map support requirements fields mismatch")
    fields = tuple(
        _text_item(item, "support field") for item in _sequence(value, "required_fields")
    )
    if fields != _SUPPORT:
        raise RadsStabilityMapError("RADS stability-map support fields are not frozen")
    if _text(value, "source_status") != "INSUFFICIENT_DATA" or _bool(
        value, "synthetic_substitution"
    ):
        raise RadsStabilityMapError("RADS stability-map support must remain fail-closed")
    _text(value, "reason")


def _validate_lineage(value: Mapping[str, object]) -> None:
    if set(value) != set(_SOURCE_DIGESTS):
        raise RadsStabilityMapError("RADS stability-map lineage fields mismatch")
    for key, expected in _SOURCE_DIGESTS.items():
        digest = _text(value, key)
        if digest != expected or not _SHA256.fullmatch(digest):
            raise RadsStabilityMapError(f"RADS stability-map {key} lineage is not frozen")


def _validate_execution(value: Mapping[str, object]) -> None:
    required = {
        "material_run_authorized",
        "r3_325_rerun",
        "write_external_artifacts",
        "theoretical_stability_claim",
        "resource_envelope",
    }
    if set(value) != required:
        raise RadsStabilityMapError("RADS stability-map execution fields mismatch")
    prohibited = (
        _bool(value, "material_run_authorized")
        or _bool(value, "r3_325_rerun")
        or _bool(value, "write_external_artifacts")
        or _bool(value, "theoretical_stability_claim")
    )
    if prohibited:
        raise RadsStabilityMapError("RADS stability-map execution must remain empirical/read-only")
    _text(value, "resource_envelope")


def _mapping(value: Mapping[str, object], key: str) -> Mapping[str, object]:
    return _mapping_item(value.get(key), key)


def _mapping_item(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RadsStabilityMapError(f"{label} must be an object")
    return value


def _sequence(value: Mapping[str, object], key: str) -> Sequence[object]:
    selected = value.get(key)
    if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes, bytearray)):
        raise RadsStabilityMapError(f"{key} must be an array")
    return selected


def _text(value: Mapping[str, object], key: str) -> str:
    selected = value.get(key)
    if not isinstance(selected, str) or not selected.strip() or len(selected) > 1024:
        raise RadsStabilityMapError(f"{key} must be non-empty text")
    return selected


def _text_item(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RadsStabilityMapError(f"{label} must be non-empty text")
    return value


def _number(value: Mapping[str, object], key: str) -> float:
    selected = value.get(key)
    if isinstance(selected, bool) or not isinstance(selected, (int, float)):
        raise RadsStabilityMapError(f"{key} must be numeric")
    return float(selected)


def _integer(value: Mapping[str, object], key: str) -> int:
    selected = value.get(key)
    if isinstance(selected, bool) or not isinstance(selected, int):
        raise RadsStabilityMapError(f"{key} must be an integer")
    return selected


def _bool(value: Mapping[str, object], key: str) -> bool:
    selected = value.get(key)
    if not isinstance(selected, bool):
        raise RadsStabilityMapError(f"{key} must be boolean")
    return selected


__all__ = [
    "RadsStabilityMapAudit",
    "RadsStabilityMapError",
    "RadsStabilityMapPlan",
    "audit_rads_stability_map_support",
    "load_rads_stability_map_plan",
]
