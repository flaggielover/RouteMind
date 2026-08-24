"""Fail-closed content-addressed RADS-BASELINE-v1 freeze for R3-340."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from pathlib import Path

from routemind_compute.application.execution import canonical_digest

_SCHEMA = "routemind-rads-baseline-v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CLAIM_BOUNDARY = "RADS_BASELINE_FREEZE_DOES_NOT_ESTABLISH_PERFORMANCE_OR_SAFETY"
_STATE_FIELDS = ("request_id", "risk_multiplier", "candidates")
_CANDIDATE_FIELDS = ("courier_id", "distance_km", "failure_probability", "impact_minutes")
_BASELINES = ("nearest", "weighted-greedy")
_VARIANTS = ("full",)
_RISK_AWARE_WEIGHT_KEYS = (
    "distance",
    "readiness",
    "overtime",
    "service_risk",
    "balance",
)
_SOURCE_PATHS = (
    "services/compute-api/src/routemind_compute/application/baselines.py",
    "services/compute-api/src/routemind_compute/application/nearest.py",
    "services/compute-api/src/routemind_compute/application/rads.py",
    "services/compute-api/src/routemind_compute/application/registry.py",
    "services/compute-api/src/routemind_compute/application/risk_aware.py",
)


class RadsBaselineError(ValueError):
    """Raised when the R3-340 baseline freeze is missing or inconsistent."""


@dataclass(frozen=True, slots=True)
class RadsBaselinePlan:
    payload: Mapping[str, object]
    baseline_digest: str
    manifest_sha256: str

    @property
    def baseline_id(self) -> str:
        return _text(self.payload, "baseline_id")


def load_rads_baseline_plan(path: Path | str) -> RadsBaselinePlan:
    """Load a RADS baseline freeze without executing a strategy or experiment."""

    manifest_path = Path(path).expanduser().resolve()
    try:
        raw = manifest_path.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RadsBaselineError("RADS baseline plan is not valid UTF-8 JSON") from exc
    if not isinstance(parsed, Mapping):
        raise RadsBaselineError("RADS baseline plan must be a JSON object")
    payload = dict(parsed)
    baseline_digest = _text(payload, "baseline_digest")
    unsigned = dict(payload)
    del unsigned["baseline_digest"]
    if canonical_digest(unsigned) != baseline_digest:
        raise RadsBaselineError("RADS baseline digest does not match content")
    _validate(payload)
    return RadsBaselinePlan(payload, baseline_digest, sha256(raw).hexdigest())


def _validate(value: Mapping[str, object]) -> None:
    required = {
        "schema_version",
        "task_id",
        "baseline_id",
        "frozen_at_utc",
        "scope",
        "state",
        "strategies",
        "objective",
        "risk",
        "selector",
        "thresholds",
        "weights",
        "fallbacks",
        "determinism",
        "limitations",
        "source_artifacts",
        "claim_boundary",
        "baseline_digest",
    }
    if set(value) != required:
        raise RadsBaselineError("RADS baseline plan fields mismatch")
    if _text(value, "schema_version") != _SCHEMA or _text(value, "task_id") != "R3-340":
        raise RadsBaselineError("RADS baseline plan identity is unsupported")
    if _text(value, "claim_boundary") != _CLAIM_BOUNDARY:
        raise RadsBaselineError("RADS baseline claim boundary is missing")
    _validate_scope(_mapping(value, "scope"))
    _validate_state(_mapping(value, "state"))
    _validate_strategies(_mapping(value, "strategies"))
    _validate_objective(_mapping(value, "objective"))
    _validate_risk(_mapping(value, "risk"))
    _validate_selector(_mapping(value, "selector"))
    _validate_thresholds(_mapping(value, "thresholds"))
    _validate_weights(_mapping(value, "weights"))
    _validate_fallbacks(_mapping(value, "fallbacks"))
    _validate_determinism(_mapping(value, "determinism"))
    _validate_limitations(_sequence(value, "limitations"))
    _validate_sources(_sequence(value, "source_artifacts"))


def _validate_scope(value: Mapping[str, object]) -> None:
    _exact(value, {"owner", "durable_truth", "hard_realtime", "purpose"}, "scope")
    for key in value:
        _text(value, key)
    if _text(value, "durable_truth") != "NONE":
        raise RadsBaselineError("RADS baseline must not own durable truth")
    if _text(value, "hard_realtime") != "NOT_AUTHORIZED":
        raise RadsBaselineError("RADS baseline is not a hard real-time authority")


def _validate_state(value: Mapping[str, object]) -> None:
    _exact(value, {"encoder", "fields", "candidate_fields", "ordering", "digest"}, "state")
    _text(value, "encoder")
    if (
        tuple(_text_mapping(item, "state field") for item in _sequence(value, "fields"))
        != _STATE_FIELDS
    ):
        raise RadsBaselineError("RADS state field order is not frozen")
    if (
        tuple(
            _text_mapping(item, "candidate field") for item in _sequence(value, "candidate_fields")
        )
        != _CANDIDATE_FIELDS
    ):
        raise RadsBaselineError("RADS candidate field order is not frozen")
    _text(value, "ordering")
    if _text(value, "digest") != "SHA-256(canonical_state_payload)":
        raise RadsBaselineError("RADS state digest rule is not frozen")


def _validate_strategies(value: Mapping[str, object]) -> None:
    _exact(
        value,
        {"control", "comparator", "rads", "baseline_order", "variants", "registry_policy"},
        "strategies",
    )
    for key, expected_name in (("control", "nearest"), ("comparator", "weighted-greedy")):
        descriptor = _mapping(value, key)
        _exact(descriptor, {"name", "version", "maturity"}, key)
        if _text(descriptor, "name") != expected_name or _text(descriptor, "version") != "1.0.0":
            raise RadsBaselineError(f"{key} strategy identity is not frozen")
        if _text(descriptor, "maturity") != "BASELINE":
            raise RadsBaselineError(f"{key} strategy maturity is not frozen")
    rads = _mapping(value, "rads")
    _exact(rads, {"name", "version", "maturity"}, "rads")
    if _text(rads, "name") != "rads" or _text(rads, "version") != "RADS-BASELINE-v1":
        raise RadsBaselineError("RADS strategy identity is not frozen")
    if _text(rads, "maturity") != "RESEARCH":
        raise RadsBaselineError("RADS strategy maturity is not frozen")
    if (
        tuple(_text_mapping(item, "baseline name") for item in _sequence(value, "baseline_order"))
        != _BASELINES
    ):
        raise RadsBaselineError("RADS baseline order is not frozen")
    if tuple(_text_mapping(item, "variant") for item in _sequence(value, "variants")) != _VARIANTS:
        raise RadsBaselineError("RADS baseline variants are not frozen")
    _text(value, "registry_policy")


def _validate_objective(value: Mapping[str, object]) -> None:
    _exact(
        value,
        {"formula", "variant", "distance_weight", "risk_weight", "risk_multiplier", "units"},
        "objective",
    )
    if _text(value, "formula") != (
        "distance_weight*distance_km + risk_weight*failure_probability*"
        "impact_minutes*risk_multiplier"
    ):
        raise RadsBaselineError("RADS objective formula is not frozen")
    if (
        _text(value, "variant") != "full"
        or _text(value, "units") != "distance_km_plus_expected_risk_minutes"
    ):
        raise RadsBaselineError("RADS objective identity is not frozen")
    if _number(value, "distance_weight") != 1.0 or _number(value, "risk_weight") != 1.0:
        raise RadsBaselineError("RADS objective weights are not frozen")
    if _number(value, "risk_multiplier") != 1.0:
        raise RadsBaselineError("RADS baseline risk multiplier is not frozen")


def _validate_risk(value: Mapping[str, object]) -> None:
    _exact(value, {"signal_fields", "failure_probability", "impact_minutes", "source"}, "risk")
    if tuple(_text_mapping(item, "risk field") for item in _sequence(value, "signal_fields")) != (
        "failure_probability",
        "impact_minutes",
    ):
        raise RadsBaselineError("RADS risk fields are not frozen")
    probability = _mapping(value, "failure_probability")
    _exact(probability, {"minimum", "maximum", "inclusive"}, "failure_probability")
    if (
        _number(probability, "minimum") != 0.0
        or _number(probability, "maximum") != 1.0
        or not _bool(probability, "inclusive")
    ):
        raise RadsBaselineError("RADS failure probability bounds are not frozen")
    impact = _mapping(value, "impact_minutes")
    _exact(impact, {"minimum", "inclusive"}, "impact_minutes")
    if _number(impact, "minimum") != 0.0 or not _bool(impact, "inclusive"):
        raise RadsBaselineError("RADS impact bounds are not frozen")
    _text(value, "source")


def _validate_selector(value: Mapping[str, object]) -> None:
    _exact(value, {"rank_key", "tie_break", "empty_candidates"}, "selector")
    if tuple(_text_mapping(item, "rank key") for item in _sequence(value, "rank_key")) != (
        "objective_total",
        "courier_id",
    ):
        raise RadsBaselineError("RADS selector rank key is not frozen")
    if (
        _text(value, "tie_break") != "lexicographic courier_id"
        or _text(value, "empty_candidates") != "explicit unassigned selection"
    ):
        raise RadsBaselineError("RADS selector policy is not frozen")


def _validate_thresholds(value: Mapping[str, object]) -> None:
    _exact(
        value,
        {"max_metadata_items", "max_text_length", "risk_multiplier", "risk_profile"},
        "thresholds",
    )
    if _integer(value, "max_metadata_items") != 32 or _integer(value, "max_text_length") != 256:
        raise RadsBaselineError("RADS bounded input thresholds are not frozen")
    if (
        _text(value, "risk_multiplier") != "finite and > 0"
        or _text(value, "risk_profile") != "exact candidate courier set"
    ):
        raise RadsBaselineError("RADS risk thresholds are not frozen")


def _validate_weights(value: Mapping[str, object]) -> None:
    _exact(value, {"rads_objective", "risk_aware_strategy", "policy"}, "weights")
    objective = _mapping(value, "rads_objective")
    _exact(objective, {"distance", "risk"}, "rads_objective")
    if _number(objective, "distance") != 1.0 or _number(objective, "risk") != 1.0:
        raise RadsBaselineError("RADS objective weight vector is not frozen")
    strategy = _mapping(value, "risk_aware_strategy")
    _exact(strategy, set(_RISK_AWARE_WEIGHT_KEYS), "risk_aware_strategy")
    expected = {
        "distance": 1.0,
        "readiness": 0.5,
        "overtime": 2.0,
        "service_risk": 2.0,
        "balance": 0.5,
    }
    if any(_number(strategy, key) != expected[key] for key in _RISK_AWARE_WEIGHT_KEYS):
        raise RadsBaselineError("risk-aware strategy weight vector is not frozen")
    _text(value, "policy")


def _validate_fallbacks(value: Mapping[str, object]) -> None:
    _exact(
        value,
        {"no_eligible", "invalid_input", "registry_failure", "silent_substitution"},
        "fallbacks",
    )
    if (
        _text(value, "no_eligible") != "explicit unassigned"
        or _text(value, "invalid_input") != "reject"
    ):
        raise RadsBaselineError("RADS fallback policy is not frozen")
    if _text(value, "registry_failure") != "raise" or _bool(value, "silent_substitution"):
        raise RadsBaselineError("RADS fallback must not silently substitute")


def _validate_determinism(value: Mapping[str, object]) -> None:
    _exact(
        value,
        {"canonical_json", "digest_algorithm", "ordering", "wall_clock_in_digest"},
        "determinism",
    )
    if (
        _text(value, "canonical_json") != "sorted keys, compact separators, UTF-8"
        or _text(value, "digest_algorithm") != "SHA-256"
    ):
        raise RadsBaselineError("RADS canonicalization policy is not frozen")
    ordering = tuple(_text_mapping(item, "ordering rule") for item in _sequence(value, "ordering"))
    if ordering != ("candidate courier_id", "baseline name", "variant order full"):
        raise RadsBaselineError("RADS ordering policy is not frozen")
    if _bool(value, "wall_clock_in_digest"):
        raise RadsBaselineError("wall-clock observations must not enter RADS digest")


def _validate_limitations(value: Sequence[object]) -> None:
    if not value or any(not isinstance(item, str) or not item.strip() for item in value):
        raise RadsBaselineError("RADS limitations must be non-empty text")


def _validate_sources(value: Sequence[object]) -> None:
    if len(value) != len(_SOURCE_PATHS):
        raise RadsBaselineError("RADS source artifact list is incomplete")
    seen: set[str] = set()
    ordered_paths: list[str] = []
    for item in value:
        source = _mapping_value(item, "source artifact")
        _exact(source, {"path", "sha256"}, "source artifact")
        path = _text(source, "path")
        if path in seen or path not in _SOURCE_PATHS:
            raise RadsBaselineError("RADS source artifact identity is invalid")
        seen.add(path)
        ordered_paths.append(path)
        digest = _text(source, "sha256")
        if not _SHA256.fullmatch(digest):
            raise RadsBaselineError("RADS source artifact digest must be SHA-256")
    if tuple(ordered_paths) != _SOURCE_PATHS:
        raise RadsBaselineError("RADS source artifacts must remain in frozen order")


def _exact(value: Mapping[str, object], allowed: set[str], label: str) -> None:
    if set(value) != allowed:
        raise RadsBaselineError(f"{label} fields mismatch")


def _mapping(value: Mapping[str, object], key: str) -> Mapping[str, object]:
    return _mapping_value(value.get(key), key)


def _mapping_value(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RadsBaselineError(f"{label} must be an object")
    return value


def _sequence(value: Mapping[str, object], key: str) -> Sequence[object]:
    selected = value.get(key)
    if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes, bytearray)):
        raise RadsBaselineError(f"{key} must be an array")
    return selected


def _text(value: Mapping[str, object], key: str) -> str:
    selected = value.get(key)
    if not isinstance(selected, str) or not selected.strip() or len(selected) > 1024:
        raise RadsBaselineError(f"{key} must be non-empty text")
    return selected


def _text_mapping(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RadsBaselineError(f"{label} must be non-empty text")
    return value


def _number(value: Mapping[str, object], key: str) -> float:
    selected = value.get(key)
    if (
        isinstance(selected, bool)
        or not isinstance(selected, (int, float))
        or not isfinite(selected)
    ):
        raise RadsBaselineError(f"{key} must be a finite number")
    return float(selected)


def _integer(value: Mapping[str, object], key: str) -> int:
    selected = value.get(key)
    if isinstance(selected, bool) or not isinstance(selected, int):
        raise RadsBaselineError(f"{key} must be an integer")
    return selected


def _bool(value: Mapping[str, object], key: str) -> bool:
    selected = value.get(key)
    if not isinstance(selected, bool):
        raise RadsBaselineError(f"{key} must be boolean")
    return selected


__all__ = ["RadsBaselineError", "RadsBaselinePlan", "load_rads_baseline_plan"]
