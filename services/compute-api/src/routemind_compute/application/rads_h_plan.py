"""Loader for the content-addressed R3-341 RADS-H formalization plan."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from pathlib import Path

from routemind_compute.application.execution import canonical_digest

_SCHEMA = "routemind-rads-h-formalization-v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CLAIM_BOUNDARY = "RADS_H_FORMALIZATION_DOES_NOT_ESTABLISH_EMPIRICAL_STABILITY_OR_PERFORMANCE"
_STATE_FIELDS = (
    "active_strategy",
    "regime_id",
    "pressure_ticks",
    "dwell_ticks",
    "switch_count",
)
_RESET_RULES = ("regime change", "below enter threshold", "outside exit band", "switch")
_SOURCE_PATHS = (
    "services/compute-api/src/routemind_compute/application/rads.py",
    "services/compute-api/src/routemind_compute/application/rads_baseline.py",
    "services/compute-api/src/routemind_compute/application/rads_h.py",
)


class RadsHPlanError(ValueError):
    """Raised when the R3-341 mechanism plan is unsafe or inconsistent."""


@dataclass(frozen=True, slots=True)
class RadsHPlan:
    payload: Mapping[str, object]
    baseline_digest: str
    manifest_sha256: str

    @property
    def mechanism_id(self) -> str:
        return _text(self.payload, "mechanism_id")


def load_rads_h_plan(path: Path | str) -> RadsHPlan:
    """Load the frozen RADS-H semantics without executing experiments."""

    plan_path = Path(path).expanduser().resolve()
    try:
        raw = plan_path.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RadsHPlanError("RADS-H plan is not valid UTF-8 JSON") from exc
    if not isinstance(parsed, Mapping):
        raise RadsHPlanError("RADS-H plan must be a JSON object")
    payload = dict(parsed)
    digest = _text(payload, "baseline_digest")
    unsigned = dict(payload)
    del unsigned["baseline_digest"]
    if canonical_digest(unsigned) != digest:
        raise RadsHPlanError("RADS-H plan digest does not match content")
    _validate(payload)
    return RadsHPlan(payload, digest, sha256(raw).hexdigest())


def _validate(value: Mapping[str, object]) -> None:
    required = {
        "schema_version",
        "task_id",
        "mechanism_id",
        "baseline_reference",
        "frozen_at_utc",
        "question",
        "parameters",
        "state",
        "transition",
        "regime",
        "cooldown_comparison",
        "limitations",
        "source_artifacts",
        "claim_boundary",
        "baseline_digest",
    }
    if set(value) != required:
        raise RadsHPlanError("RADS-H plan fields mismatch")
    if _text(value, "schema_version") != _SCHEMA or _text(value, "task_id") != "R3-341":
        raise RadsHPlanError("RADS-H plan identity is unsupported")
    if _text(value, "mechanism_id") != "RADS-H-v1":
        raise RadsHPlanError("RADS-H mechanism identity is not frozen")
    if _text(value, "baseline_reference") != "RADS-BASELINE-v1":
        raise RadsHPlanError("RADS-H baseline reference is not frozen")
    if _text(value, "claim_boundary") != _CLAIM_BOUNDARY:
        raise RadsHPlanError("RADS-H claim boundary is missing")
    _text(value, "frozen_at_utc")
    _text(value, "question")
    _validate_parameters(_mapping(value, "parameters"))
    _validate_state(_mapping(value, "state"))
    _validate_transition(_mapping(value, "transition"))
    _validate_regime(_mapping(value, "regime"))
    _validate_cooldown(_mapping(value, "cooldown_comparison"))
    _validate_limitations(_sequence(value, "limitations"))
    _validate_sources(_sequence(value, "source_artifacts"))


def _validate_parameters(value: Mapping[str, object]) -> None:
    _exact(
        value,
        {
            "enter_threshold",
            "exit_threshold",
            "persistence_ticks",
            "minimum_dwell_ticks",
            "switching_cost",
        },
        "parameters",
    )
    enter = _number(value, "enter_threshold")
    exit_threshold = _number(value, "exit_threshold")
    if enter != 0.05 or exit_threshold != 0.02 or exit_threshold >= enter:
        raise RadsHPlanError("RADS-H threshold band is not frozen")
    if _integer(value, "persistence_ticks") != 2 or _integer(value, "minimum_dwell_ticks") != 3:
        raise RadsHPlanError("RADS-H persistence or dwell is not frozen")
    if _number(value, "switching_cost") != 0.01:
        raise RadsHPlanError("RADS-H switching cost is not frozen")


def _validate_state(value: Mapping[str, object]) -> None:
    _exact(value, {"fields", "pressure_definition", "reset_rules", "state_owner"}, "state")
    if (
        tuple(_text_mapping(item, "state field") for item in _sequence(value, "fields"))
        != _STATE_FIELDS
    ):
        raise RadsHPlanError("RADS-H state fields are not frozen")
    if (
        tuple(_text_mapping(item, "reset rule") for item in _sequence(value, "reset_rules"))
        != _RESET_RULES
    ):
        raise RadsHPlanError("RADS-H reset rules are not frozen")
    _text(value, "pressure_definition")
    _text(value, "state_owner")


def _validate_transition(value: Mapping[str, object]) -> None:
    _exact(
        value, {"advantage_formula", "enter", "exit", "switch_action", "hold_action"}, "transition"
    )
    expected = {
        "advantage_formula": "(current_score-candidate_score)/max(abs(current_score),1e-12)",
        "enter": "advantage >= enter_threshold and persistence_ticks reached after minimum dwell",
        "exit": "advantage < -exit_threshold resets pressure and holds",
        "switch_action": "emit switch proposal, apply switching_cost, reset pressure and dwell",
        "hold_action": "retain active strategy and emit explicit reason",
    }
    if any(_text(value, key) != expected[key] for key in expected):
        raise RadsHPlanError("RADS-H transition semantics are not frozen")


def _validate_regime(value: Mapping[str, object]) -> None:
    _exact(value, {"identity_field", "required", "change_behavior"}, "regime")
    if _text(value, "identity_field") != "regime_id" or not _bool(value, "required"):
        raise RadsHPlanError("RADS-H regime identity is not frozen")
    if (
        _text(value, "change_behavior")
        != "reset pressure and dwell, hold, then collect fresh pressure"
    ):
        raise RadsHPlanError("RADS-H regime change behavior is not frozen")


def _validate_cooldown(value: Mapping[str, object]) -> None:
    _exact(value, {"cooldown_only", "rads_h", "separation"}, "cooldown_comparison")
    if _text(value, "cooldown_only") != "minimum dwell without pressure threshold or persistence":
        raise RadsHPlanError("cooldown comparator is not explicit")
    if (
        _text(value, "rads_h")
        != "threshold band plus consecutive pressure persistence and switching cost"
    ):
        raise RadsHPlanError("RADS-H comparator semantics are not explicit")
    if _text(value, "separation") != "cooldown is a comparator, not RADS-H":
        raise RadsHPlanError("cooldown and RADS-H must remain separate")


def _validate_limitations(value: Sequence[object]) -> None:
    if not value or any(not isinstance(item, str) or not item.strip() for item in value):
        raise RadsHPlanError("RADS-H limitations must be non-empty text")


def _validate_sources(value: Sequence[object]) -> None:
    if len(value) != len(_SOURCE_PATHS):
        raise RadsHPlanError("RADS-H source artifact list is incomplete")
    seen: set[str] = set()
    ordered: list[str] = []
    for item in value:
        source = _mapping_value(item, "source artifact")
        _exact(source, {"path", "sha256"}, "source artifact")
        path = _text(source, "path")
        if path in seen or path not in _SOURCE_PATHS:
            raise RadsHPlanError("RADS-H source artifact identity is invalid")
        seen.add(path)
        ordered.append(path)
        if not _SHA256.fullmatch(_text(source, "sha256")):
            raise RadsHPlanError("RADS-H source artifact digest must be SHA-256")
    if tuple(ordered) != _SOURCE_PATHS:
        raise RadsHPlanError("RADS-H source artifact order is not frozen")


def _exact(value: Mapping[str, object], allowed: set[str], label: str) -> None:
    if set(value) != allowed:
        raise RadsHPlanError(f"{label} fields mismatch")


def _mapping(value: Mapping[str, object], key: str) -> Mapping[str, object]:
    return _mapping_value(value.get(key), key)


def _mapping_value(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RadsHPlanError(f"{label} must be an object")
    return value


def _sequence(value: Mapping[str, object], key: str) -> Sequence[object]:
    selected = value.get(key)
    if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes, bytearray)):
        raise RadsHPlanError(f"{key} must be an array")
    return selected


def _text(value: Mapping[str, object], key: str) -> str:
    selected = value.get(key)
    if not isinstance(selected, str) or not selected.strip() or len(selected) > 1024:
        raise RadsHPlanError(f"{key} must be non-empty text")
    return selected


def _text_mapping(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RadsHPlanError(f"{label} must be non-empty text")
    return value


def _number(value: Mapping[str, object], key: str) -> float:
    selected = value.get(key)
    if (
        isinstance(selected, bool)
        or not isinstance(selected, (int, float))
        or not isfinite(selected)
    ):
        raise RadsHPlanError(f"{key} must be a finite number")
    return float(selected)


def _integer(value: Mapping[str, object], key: str) -> int:
    selected = value.get(key)
    if isinstance(selected, bool) or not isinstance(selected, int):
        raise RadsHPlanError(f"{key} must be an integer")
    return selected


def _bool(value: Mapping[str, object], key: str) -> bool:
    selected = value.get(key)
    if not isinstance(selected, bool):
        raise RadsHPlanError(f"{key} must be boolean")
    return selected


__all__ = ["RadsHPlan", "RadsHPlanError", "load_rads_h_plan"]
