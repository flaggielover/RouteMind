"""Explicit What-if validity boundaries for R3-335."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Literal

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.twin_held_out_validation import (
    TwinHeldOutValidationOutcome,
)

_SCHEMA = "routemind-twin-what-if-validity-v1"
_CLAIM_BOUNDARY = "WHAT_IF_BOUNDARIES_DO_NOT_ESTABLISH_CAUSAL_OR_EXTERNAL_VALIDITY"
_MODES = ("counterfactual_replay", "simulation_comparison", "causal_inference")
_STATUS = Literal["NO_VALIDITY_CLAIM", "SCOPE_ONLY"]


class TwinWhatIfValidityError(ValueError):
    """Raised when What-if validity boundaries or lineage are unsafe."""


@dataclass(frozen=True, slots=True)
class TwinWhatIfValidityPlan:
    payload: Mapping[str, object]
    plan_digest: str
    manifest_sha256: str

    @property
    def boundary_id(self) -> str:
        return _text(self.payload, "boundary_id")


@dataclass(frozen=True, slots=True)
class WhatIfModeStatus:
    mode_id: str
    status: str
    allowed_interpretation: str
    prohibited_claims: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TwinWhatIfValidityOutcome:
    status: _STATUS
    plan_digest: str
    validation_plan_digest: str
    allowed_scope: tuple[str, ...]
    modes: tuple[WhatIfModeStatus, ...]
    reason: str
    claim_boundary: str = _CLAIM_BOUNDARY


def load_twin_what_if_validity_plan(path: Path | str) -> TwinWhatIfValidityPlan:
    """Load a content-addressed What-if boundary plan without running a replay."""

    plan_path = Path(path).expanduser().resolve()
    try:
        raw = plan_path.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TwinWhatIfValidityError("Twin What-if validity plan is not valid UTF-8 JSON") from exc
    if not isinstance(parsed, Mapping):
        raise TwinWhatIfValidityError("Twin What-if validity plan must be a JSON object")
    payload = dict(parsed)
    plan_digest = _text(payload, "plan_digest")
    unsigned = dict(payload)
    del unsigned["plan_digest"]
    if canonical_digest(unsigned) != plan_digest:
        raise TwinWhatIfValidityError("Twin What-if validity plan digest does not match content")
    _validate(payload)
    return TwinWhatIfValidityPlan(payload, plan_digest, sha256(raw).hexdigest())


def assess_twin_what_if_validity(
    plan: TwinWhatIfValidityPlan,
    validation_outcome: TwinHeldOutValidationOutcome,
) -> TwinWhatIfValidityOutcome:
    """Derive wording from held-out evidence; never infer causal validity."""

    if _text(plan.payload, "source_validation_plan_digest") != validation_outcome.plan_digest:
        raise TwinWhatIfValidityError("validation plan digest does not match What-if boundary plan")
    modes = tuple(
        _mode_result(item, validation_outcome.outcome == "INSUFFICIENT_DATA")
        for item in _sequence(plan.payload, "mode_policies")
    )
    if validation_outcome.outcome == "INSUFFICIENT_DATA":
        return TwinWhatIfValidityOutcome(
            status="NO_VALIDITY_CLAIM",
            plan_digest=plan.plan_digest,
            validation_plan_digest=validation_outcome.plan_digest,
            allowed_scope=(),
            modes=modes,
            reason=_text(_mapping(plan.payload, "scope_policy"), "when_insufficient_data"),
        )
    return TwinWhatIfValidityOutcome(
        status="SCOPE_ONLY",
        plan_digest=plan.plan_digest,
        validation_plan_digest=validation_outcome.plan_digest,
        allowed_scope=("observed_held_out_scope_only",),
        modes=modes,
        reason=_text(_mapping(plan.payload, "scope_policy"), "when_supported"),
    )


def _validate(value: Mapping[str, object]) -> None:
    required = {
        "schema_version",
        "task_id",
        "boundary_id",
        "frozen_at_utc",
        "question",
        "source_validation_plan_digest",
        "mode_policies",
        "scope_policy",
        "claim_boundary",
        "plan_digest",
    }
    if set(value) != required:
        raise TwinWhatIfValidityError("Twin What-if validity plan fields mismatch")
    if _text(value, "schema_version") != _SCHEMA or _text(value, "task_id") != "R3-335":
        raise TwinWhatIfValidityError("Twin What-if validity plan identity is unsupported")
    if _text(value, "claim_boundary") != _CLAIM_BOUNDARY:
        raise TwinWhatIfValidityError("What-if claim boundary is missing")
    _text(value, "question")
    _digest(value, "source_validation_plan_digest")
    policies = _sequence(value, "mode_policies")
    if len(policies) != len(_MODES):
        raise TwinWhatIfValidityError("exactly three What-if modes are required")
    for expected, item in zip(_MODES, policies, strict=True):
        mode = _mapping_value(item, "mode")
        _exact(mode, {"mode_id", "allowed_interpretation", "prohibited_claims"}, "mode")
        if _text(mode, "mode_id") != expected:
            raise TwinWhatIfValidityError("What-if mode identity/order is not frozen")
        _text(mode, "allowed_interpretation")
        claims = _sequence(mode, "prohibited_claims")
        if not claims:
            raise TwinWhatIfValidityError("each What-if mode needs prohibited claims")
        for claim in claims:
            _text_mapping(claim, "prohibited claim")
    scope = _mapping(value, "scope_policy")
    _exact(scope, {"when_insufficient_data", "when_supported", "external_validity"}, "scope_policy")
    if _text(scope, "when_insufficient_data") != "NO_VALIDITY_CLAIM":
        raise TwinWhatIfValidityError("insufficient data must prohibit validity claims")
    if _text(scope, "when_supported") != "SCOPE_ONLY":
        raise TwinWhatIfValidityError("supported wording must remain scope-only")
    if _text(scope, "external_validity") != "PROHIBITED":
        raise TwinWhatIfValidityError("external-validity wording is prohibited")


def _mode_result(value: object, no_data: bool) -> WhatIfModeStatus:
    mode = _mapping_value(value, "mode")
    mode_id = _text(mode, "mode_id")
    return WhatIfModeStatus(
        mode_id,
        "BOUNDARY_ONLY" if no_data else "SCOPE_ONLY",
        _text(mode, "allowed_interpretation"),
        tuple(
            _text_mapping(claim, "prohibited claim")
            for claim in _sequence(mode, "prohibited_claims")
        ),
    )


def _exact(value: Mapping[str, object], allowed: set[str], label: str) -> None:
    if set(value) != allowed:
        raise TwinWhatIfValidityError(f"{label} fields mismatch")


def _mapping(value: Mapping[str, object], key: str) -> Mapping[str, object]:
    return _mapping_value(value.get(key), key)


def _mapping_value(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TwinWhatIfValidityError(f"{label} must be an object")
    return value


def _sequence(value: Mapping[str, object], key: str) -> Sequence[object]:
    selected = value.get(key)
    if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes, bytearray)):
        raise TwinWhatIfValidityError(f"{key} must be an array")
    return selected


def _text(value: Mapping[str, object], key: str) -> str:
    selected = value.get(key)
    if not isinstance(selected, str) or not selected.strip() or len(selected) > 1024:
        raise TwinWhatIfValidityError(f"{key} must be non-empty text")
    return selected


def _text_mapping(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TwinWhatIfValidityError(f"{label} must be non-empty text")
    return value


def _digest(value: Mapping[str, object], key: str) -> str:
    selected = _text(value, key)
    if len(selected) != 64 or any(char not in "0123456789abcdef" for char in selected):
        raise TwinWhatIfValidityError(f"{key} must be a SHA-256 digest")
    return selected


__all__ = [
    "TwinWhatIfValidityError",
    "TwinWhatIfValidityOutcome",
    "TwinWhatIfValidityPlan",
    "WhatIfModeStatus",
    "assess_twin_what_if_validity",
    "load_twin_what_if_validity_plan",
]
