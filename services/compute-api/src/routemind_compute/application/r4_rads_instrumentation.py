"""Versioned tick-level RADS instrumentation for future research campaigns.

This contract records observations; it does not infer a treatment effect or fill
missing fields. A failed instrumentation call is retained as an explicit failure
record so a later campaign cannot silently turn missing telemetry into zeros.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Literal

InstrumentationStatus = Literal["RECORDED", "FAILED"]
ConstraintStatus = Literal["SATISFIED", "VIOLATED", "UNAVAILABLE"]
SCHEMA_VERSION = "routemind-rads-tick-v1"
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Za-z0-9._:/@-]{1,160}$")


def canonical_digest(value: Any) -> str:
    return sha256(
        json.dumps(
            value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _id(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or not _ID.fullmatch(value):
        raise ValueError(f"{name} must be a safe non-empty identifier")
    return value


def _digest(value: str, name: str) -> str:
    if not _DIGEST.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


@dataclass(frozen=True, slots=True)
class RadsTick:
    run_id: str
    manifest_digest: str
    request_id: str
    tick: int
    variant: str
    policy_version: str
    state_digest: str
    action_id: str
    action_set: tuple[str, ...]
    previous_policy: str
    selected_policy: str
    switch_occurred: bool
    constraint_status: ConstraintStatus
    fallback_state: str
    latency_ms: float
    outcome_status: str
    outcome_digest: str
    lineage_digest: str
    tenant_key: str = "rtk_unattributed"

    def __post_init__(self) -> None:
        for value, name in (
            (self.run_id, "run_id"),
            (self.request_id, "request_id"),
            (self.variant, "variant"),
            (self.policy_version, "policy_version"),
            (self.action_id, "action_id"),
            (self.previous_policy, "previous_policy"),
            (self.selected_policy, "selected_policy"),
            (self.fallback_state, "fallback_state"),
            (self.outcome_status, "outcome_status"),
            (self.tenant_key, "tenant_key"),
        ):
            _id(value, name)
        for value, name in (
            (self.manifest_digest, "manifest_digest"),
            (self.state_digest, "state_digest"),
            (self.outcome_digest, "outcome_digest"),
            (self.lineage_digest, "lineage_digest"),
        ):
            _digest(value, name)
        if self.tick < 0:
            raise ValueError("tick must be non-negative")
        if not self.action_set or len(set(self.action_set)) != len(self.action_set):
            raise ValueError("action_set must contain unique actions")
        if any(not _ID.fullmatch(item) for item in self.action_set):
            raise ValueError("action_set contains an unsafe action")
        if self.action_id not in self.action_set:
            raise ValueError("action_id must be present in action_set")
        if self.switch_occurred != (self.previous_policy != self.selected_policy):
            raise ValueError("switch_occurred must match policy transition")
        if self.constraint_status not in {"SATISFIED", "VIOLATED", "UNAVAILABLE"}:
            raise ValueError("unsupported constraint_status")
        if self.latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "manifest_digest": self.manifest_digest,
            "request_id": self.request_id,
            "tick": self.tick,
            "variant": self.variant,
            "policy_version": self.policy_version,
            "state_digest": self.state_digest,
            "action_id": self.action_id,
            "action_set": self.action_set,
            "previous_policy": self.previous_policy,
            "selected_policy": self.selected_policy,
            "switch_occurred": self.switch_occurred,
            "constraint_status": self.constraint_status,
            "fallback_state": self.fallback_state,
            "latency_ms": self.latency_ms,
            "outcome_status": self.outcome_status,
            "outcome_digest": self.outcome_digest,
            "lineage_digest": self.lineage_digest,
            "tenant_key": self.tenant_key,
            "claim_boundary": "observational_only",
        }


@dataclass(frozen=True, slots=True)
class RadsInstrumentationFailure:
    run_id: str
    tick: int
    reason: str
    missing_fields: tuple[str, ...]
    status: InstrumentationStatus = "FAILED"

    def __post_init__(self) -> None:
        _id(self.run_id, "run_id")
        if self.tick < 0:
            raise ValueError("tick must be non-negative")
        if not self.reason.strip() or not self.missing_fields:
            raise ValueError("failure reason and missing_fields are required")
        if len(set(self.missing_fields)) != len(self.missing_fields):
            raise ValueError("missing_fields must be unique")

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "tick": self.tick,
            "status": self.status,
            "reason": self.reason,
            "missing_fields": self.missing_fields,
        }


class RadsInstrumentationRecorder:
    """Append-only recorder for complete ticks and explicit failures."""

    REQUIRED_FIELDS = (
        "manifest_digest",
        "request_id",
        "variant",
        "state_digest",
        "action_id",
        "action_set",
        "constraint_status",
        "fallback_state",
        "latency_ms",
        "outcome_status",
        "outcome_digest",
        "lineage_digest",
    )

    def __init__(self) -> None:
        self._ticks: list[RadsTick] = []
        self._failures: list[RadsInstrumentationFailure] = []

    @property
    def ticks(self) -> tuple[RadsTick, ...]:
        return tuple(self._ticks)

    @property
    def failures(self) -> tuple[RadsInstrumentationFailure, ...]:
        return tuple(self._failures)

    def record(self, **values: Any) -> RadsTick:
        missing = tuple(
            field for field in self.REQUIRED_FIELDS if field not in values or values[field] is None
        )
        if missing:
            run_id = values.get("run_id")
            tick = values.get("tick")
            if isinstance(run_id, str) and isinstance(tick, int):
                self._failures.append(
                    RadsInstrumentationFailure(run_id, tick, "required_field_missing", missing)
                )
            raise ValueError(f"required instrumentation fields missing: {', '.join(missing)}")
        tick = RadsTick(**values)
        self._ticks.append(tick)
        return tick

    def record_failure(
        self, *, run_id: str, tick: int, reason: str, missing_fields: tuple[str, ...]
    ) -> RadsInstrumentationFailure:
        failure = RadsInstrumentationFailure(run_id, tick, reason, missing_fields)
        self._failures.append(failure)
        return failure

    def metrics(self) -> dict[str, object]:
        variants = Counter(item.variant for item in self._ticks)
        return {
            "schema_version": SCHEMA_VERSION,
            "tick_count": len(self._ticks),
            "failure_count": len(self._failures),
            "switch_count": sum(item.switch_occurred for item in self._ticks),
            "constraint_violations": sum(
                item.constraint_status == "VIOLATED" for item in self._ticks
            ),
            "fallback_count": sum(item.fallback_state != "NONE" for item in self._ticks),
            "variant_counts": tuple(sorted(variants.items())),
            "claim_boundary": "observational_only",
        }

    def replay_digest(self) -> str:
        return canonical_digest(
            {
                "ticks": [item.as_dict() for item in self._ticks],
                "failures": [item.as_dict() for item in self._failures],
            }
        )


__all__ = [
    "SCHEMA_VERSION",
    "RadsInstrumentationFailure",
    "RadsInstrumentationRecorder",
    "RadsTick",
    "canonical_digest",
]
