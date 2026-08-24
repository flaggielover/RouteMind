"""Fail-closed loader for the R3-352 simulation-only switchback design."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from itertools import pairwise
from pathlib import Path

from routemind_compute.application.execution import canonical_digest

_SCHEMA = "routemind-switchback-design-v1"
_CLAIM_BOUNDARY = "SIMULATION_DESIGN_NOT_REAL_WORLD_CAUSAL_VALIDATION"


class SwitchbackDesignError(ValueError):
    """Raised when a switchback design is not a valid preregistration."""


@dataclass(frozen=True, slots=True)
class SwitchbackDesign:
    payload: Mapping[str, object]
    design_digest: str
    manifest_sha256: str

    @property
    def design_id(self) -> str:
        return _text(self.payload, "design_id")

    @property
    def period_count(self) -> int:
        return len(_sequence(self.payload, "periods"))

    @property
    def zone_count(self) -> int:
        return len(_sequence(self.payload, "zones"))


def load_switchback_design(path: Path | str) -> SwitchbackDesign:
    """Load and semantically validate a frozen design without running it."""

    design_path = Path(path).expanduser().resolve()
    try:
        raw = design_path.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SwitchbackDesignError("switchback design is not valid UTF-8 JSON") from exc
    if not isinstance(parsed, Mapping):
        raise SwitchbackDesignError("switchback design must be a JSON object")
    payload = dict(parsed)
    design_digest = _text(payload, "design_digest")
    unsigned = dict(payload)
    del unsigned["design_digest"]
    if canonical_digest(unsigned) != design_digest:
        raise SwitchbackDesignError("switchback design digest does not match content")
    _validate(payload)
    return SwitchbackDesign(payload, design_digest, sha256(raw).hexdigest())


def _validate(value: Mapping[str, object]) -> None:
    required = {
        "schema_version",
        "task_id",
        "design_id",
        "frozen_at_utc",
        "phase",
        "scope",
        "seed",
        "zones",
        "periods",
        "assignment",
        "washout",
        "interference_risks",
        "metrics",
        "analysis",
        "claim_boundary",
        "design_digest",
    }
    if set(value) != required:
        raise SwitchbackDesignError("switchback design fields mismatch")
    if _text(value, "schema_version") != _SCHEMA or _text(value, "task_id") != "R3-352":
        raise SwitchbackDesignError("switchback design identity is unsupported")
    if _text(value, "phase") != "simulation-only":
        raise SwitchbackDesignError("switchback design must be simulation-only")
    if _integer(value, "seed") < 0:
        raise SwitchbackDesignError("switchback seed must be non-negative")
    zones = _text_sequence(value, "zones")
    if len(zones) < 2 or len(set(zones)) != len(zones):
        raise SwitchbackDesignError("switchback design needs two unique zones")
    _validate_periods(value, set(zones))
    _validate_assignment(_mapping(value, "assignment"))
    _validate_washout(_mapping(value, "washout"))
    _validate_interference(_sequence(value, "interference_risks"))
    _validate_metrics(_mapping(value, "metrics"))
    analysis = _mapping(value, "analysis")
    _exact(
        analysis,
        {"comparison_unit", "cluster", "descriptive_only", "causal_claim_allowed"},
        "analysis",
    )
    if not _bool(analysis, "descriptive_only") or _bool(analysis, "causal_claim_allowed"):
        raise SwitchbackDesignError("switchback analysis must remain descriptive")
    if _text(value, "claim_boundary") != _CLAIM_BOUNDARY:
        raise SwitchbackDesignError("switchback claim boundary is missing")


def _validate_periods(value: Mapping[str, object], zones: set[str]) -> None:
    periods = _sequence(value, "periods")
    if len(periods) < 4:
        raise SwitchbackDesignError("switchback design needs at least four periods")
    arms: list[str] = []
    indices: list[int] = []
    for item in periods:
        period = _mapping_value(item, "period")
        _exact(
            period,
            {
                "period_id",
                "block_index",
                "arm",
                "duration_ticks",
                "warmup_ticks",
                "washout_ticks",
                "zone_ids",
            },
            "period",
        )
        period_zones = set(_text_sequence(period, "zone_ids"))
        if not period_zones or not period_zones.issubset(zones):
            raise SwitchbackDesignError("period zone_ids must be a non-empty subset of zones")
        duration = _integer(period, "duration_ticks")
        warmup = _integer(period, "warmup_ticks")
        washout = _integer(period, "washout_ticks")
        if min(duration, warmup, washout) < 0 or duration <= warmup + washout:
            raise SwitchbackDesignError(
                "period duration must leave an estimable post-washout window"
            )
        arms.append(_text(period, "arm"))
        indices.append(_integer(period, "block_index"))
    if len(indices) != len(set(indices)) or sorted(indices) != list(range(len(indices))):
        raise SwitchbackDesignError("period block_index values must be consecutive and unique")
    if any(arm not in {"candidate", "comparator"} for arm in arms):
        raise SwitchbackDesignError("period arm must be candidate or comparator")
    if any(first == second for first, second in pairwise(arms)):
        raise SwitchbackDesignError("arms must alternate between adjacent periods")
    if set(arms) != {"candidate", "comparator"}:
        raise SwitchbackDesignError("both switchback arms must be represented")


def _validate_assignment(value: Mapping[str, object]) -> None:
    _exact(
        value,
        {"unit", "method", "seed_derivation", "per_order_randomization_allowed", "balance_rule"},
        "assignment",
    )
    if _text(value, "unit") != "zone_time_block":
        raise SwitchbackDesignError("assignment unit must be zone_time_block")
    if _text(value, "method") != "deterministic_seeded_block_sequence":
        raise SwitchbackDesignError("assignment method is unsupported")
    if _bool(value, "per_order_randomization_allowed"):
        raise SwitchbackDesignError("per-order randomization is prohibited")
    _require_text(value, "seed_derivation")
    _require_text(value, "balance_rule")


def _validate_washout(value: Mapping[str, object]) -> None:
    _exact(value, {"ticks", "rule", "excluded_from_primary_window"}, "washout")
    if _integer(value, "ticks") <= 0 or not _bool(value, "excluded_from_primary_window"):
        raise SwitchbackDesignError("washout must be positive and excluded from the primary window")
    _require_text(value, "rule")


def _validate_interference(value: Sequence[object]) -> None:
    if len(value) < 3:
        raise SwitchbackDesignError("shared-supply interference risks are incomplete")
    required = {"shared-supply", "zone-spillover", "carryover"}
    found: set[str] = set()
    for item in value:
        risk = _mapping_value(item, "interference risk")
        _exact(
            risk,
            {"risk_id", "mechanism", "unit", "spillover", "mitigation", "diagnostic"},
            "interference risk",
        )
        found.add(_text(risk, "risk_id"))
        for key in ("mechanism", "unit", "spillover", "mitigation", "diagnostic"):
            _require_text(risk, key)
    if not required.issubset(found):
        raise SwitchbackDesignError("required shared-supply interference risks are missing")


def _validate_metrics(value: Mapping[str, object]) -> None:
    _exact(value, {"primary", "secondary", "not_estimable_without_outcomes"}, "metrics")
    primary = _text_sequence(value, "primary")
    secondary = _text_sequence(value, "secondary")
    if (
        not primary
        or not secondary
        or any("causal" in metric.lower() for metric in (*primary, *secondary))
    ):
        raise SwitchbackDesignError("metrics must be descriptive and non-causal")
    _require_text(value, "not_estimable_without_outcomes")


def _exact(value: Mapping[str, object], allowed: set[str], label: str) -> None:
    if set(value) != allowed:
        raise SwitchbackDesignError(f"{label} fields mismatch")


def _mapping(value: Mapping[str, object], key: str) -> Mapping[str, object]:
    return _mapping_value(value.get(key), key)


def _mapping_value(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise SwitchbackDesignError(f"{label} must be an object")
    return value


def _sequence(value: Mapping[str, object], key: str) -> Sequence[object]:
    selected = value.get(key)
    if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes, bytearray)):
        raise SwitchbackDesignError(f"{key} must be an array")
    return selected


def _text_sequence(value: Mapping[str, object], key: str) -> tuple[str, ...]:
    selected = _sequence(value, key)
    result = tuple(_text_item(item, key) for item in selected)
    return result


def _text(value: Mapping[str, object], key: str) -> str:
    return _text_item(value.get(key), key)


def _text_item(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 1024:
        raise SwitchbackDesignError(f"{label} must be non-empty text")
    return value


def _require_text(value: Mapping[str, object], key: str) -> None:
    _text(value, key)


def _integer(value: Mapping[str, object], key: str) -> int:
    selected = value.get(key)
    if isinstance(selected, bool) or not isinstance(selected, int):
        raise SwitchbackDesignError(f"{key} must be an integer")
    return selected


def _bool(value: Mapping[str, object], key: str) -> bool:
    selected = value.get(key)
    if not isinstance(selected, bool):
        raise SwitchbackDesignError(f"{key} must be boolean")
    return selected


__all__ = ["SwitchbackDesign", "SwitchbackDesignError", "load_switchback_design"]
