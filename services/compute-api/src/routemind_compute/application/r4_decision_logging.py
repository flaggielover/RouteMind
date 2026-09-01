"""Decision-time support logging for a future off-policy audit.

The store is intentionally descriptive. It records exact propensities when the
policy supplies them and records deterministic actions as such; it never
reconstructs or fabricates a propensity after the decision has happened.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from typing import Literal

ActionMode = Literal["STOCHASTIC", "DETERMINISTIC"]
SCHEMA_VERSION = "routemind-decision-log-v1"
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Za-z0-9._:/@-]{1,160}$")
_TENANT = re.compile(r"^rtk_(?:[0-9a-f]{8,64}|unattributed|overflow)$")


def canonical_digest(value: object) -> str:
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
class DecisionLogRecord:
    decision_id: str
    tenant_key: str
    policy_id: str
    policy_version: str
    action_set: tuple[str, ...]
    selected_action: str
    action_mode: ActionMode
    propensity: float | None
    state_digest: str
    shared_resource_digest: str
    outcome_digest: str
    decision_sequence: int
    record_digest: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.decision_id, "decision_id"),
            (self.policy_id, "policy_id"),
            (self.policy_version, "policy_version"),
            (self.selected_action, "selected_action"),
        ):
            _id(value, name)
        if not _TENANT.fullmatch(self.tenant_key):
            raise ValueError("tenant_key must be a pseudonymized rtk_ key")
        for value, name in (
            (self.state_digest, "state_digest"),
            (self.shared_resource_digest, "shared_resource_digest"),
            (self.outcome_digest, "outcome_digest"),
        ):
            _digest(value, name)
        if not self.action_set or len(set(self.action_set)) != len(self.action_set):
            raise ValueError("action_set must contain unique actions")
        if any(not _ID.fullmatch(item) for item in self.action_set):
            raise ValueError("action_set contains an unsafe action")
        if self.selected_action not in self.action_set:
            raise ValueError("selected_action must be in action_set")
        if self.action_mode not in {"STOCHASTIC", "DETERMINISTIC"}:
            raise ValueError("unsupported action_mode")
        if self.action_mode == "DETERMINISTIC" and self.propensity is not None:
            raise ValueError("deterministic decisions must not contain a fabricated propensity")
        if self.action_mode == "STOCHASTIC" and (
            self.propensity is None or not isfinite(self.propensity) or not 0 < self.propensity <= 1
        ):
            raise ValueError("stochastic decisions require a propensity in (0, 1]")
        if self.decision_sequence < 0:
            raise ValueError("decision_sequence must be non-negative")
        if self.record_digest != canonical_digest(self.canonical_payload()):
            raise ValueError("record_digest does not match decision-time payload")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "decision_id": self.decision_id,
            "tenant_key": self.tenant_key,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "action_set": self.action_set,
            "selected_action": self.selected_action,
            "action_mode": self.action_mode,
            "propensity": self.propensity,
            "state_digest": self.state_digest,
            "shared_resource_digest": self.shared_resource_digest,
            "outcome_digest": self.outcome_digest,
            "decision_sequence": self.decision_sequence,
            "capture_boundary": "decision_time_only",
        }

    @classmethod
    def create(
        cls,
        *,
        decision_id: str,
        tenant_key: str,
        policy_id: str,
        policy_version: str,
        action_set: tuple[str, ...],
        selected_action: str,
        action_mode: ActionMode,
        propensity: float | None,
        state_digest: str,
        shared_resource_digest: str,
        outcome_digest: str,
        decision_sequence: int,
    ) -> DecisionLogRecord:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "decision_id": decision_id,
            "tenant_key": tenant_key,
            "policy_id": policy_id,
            "policy_version": policy_version,
            "action_set": action_set,
            "selected_action": selected_action,
            "action_mode": action_mode,
            "propensity": propensity,
            "state_digest": state_digest,
            "shared_resource_digest": shared_resource_digest,
            "outcome_digest": outcome_digest,
            "decision_sequence": decision_sequence,
            "capture_boundary": "decision_time_only",
        }
        return cls(
            decision_id,
            tenant_key,
            policy_id,
            policy_version,
            action_set,
            selected_action,
            action_mode,
            propensity,
            state_digest,
            shared_resource_digest,
            outcome_digest,
            decision_sequence,
            canonical_digest(payload),
        )

    def as_dict(self) -> dict[str, object]:
        return self.canonical_payload() | {"record_digest": self.record_digest}


@dataclass(frozen=True, slots=True)
class DecisionLoggingPolicy:
    max_records: int = 100_000
    retention_days: int = 365

    def __post_init__(self) -> None:
        if self.max_records <= 0 or self.retention_days <= 0:
            raise ValueError("decision logging limits must be positive")


@dataclass(frozen=True, slots=True)
class SupportAudit:
    record_count: int
    stochastic_count: int
    deterministic_count: int
    action_counts: tuple[tuple[str, int], ...]
    shared_resource_count: int
    overlap_ratio: float
    status: str
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_count": self.record_count,
            "stochastic_count": self.stochastic_count,
            "deterministic_count": self.deterministic_count,
            "action_counts": self.action_counts,
            "shared_resource_count": self.shared_resource_count,
            "overlap_ratio": self.overlap_ratio,
            "status": self.status,
            "reason": self.reason,
            "claim_boundary": "support_diagnostic_only",
        }


class DecisionLogStore:
    """Bounded append-only decision-time log with support diagnostics."""

    def __init__(self, policy: DecisionLoggingPolicy | None = None) -> None:
        self.policy = policy or DecisionLoggingPolicy()
        self._records: dict[str, DecisionLogRecord] = {}

    @property
    def records(self) -> tuple[DecisionLogRecord, ...]:
        return tuple(self._records.values())

    def append(self, record: DecisionLogRecord, *, captured_at_decision: bool = True) -> None:
        if not captured_at_decision:
            raise ValueError("retroactive propensity or decision logging is forbidden")
        if record.decision_id in self._records:
            raise ValueError("duplicate decision_id")
        if len(self._records) >= self.policy.max_records:
            raise ValueError("decision log retention limit exceeded")
        self._records[record.decision_id] = record

    def audit_support(self) -> SupportAudit:
        records = self.records
        if not records:
            return SupportAudit(0, 0, 0, (), 0, 0.0, "INSUFFICIENT_DATA", "no decision-time logs")
        action_counts = Counter(record.selected_action for record in records)
        available = set.intersection(*(set(record.action_set) for record in records))
        union = set.union(*(set(record.action_set) for record in records))
        overlap = len(available) / len(union) if union else 0.0
        stochastic = sum(record.action_mode == "STOCHASTIC" for record in records)
        deterministic = len(records) - stochastic
        if stochastic == 0:
            status = "OPE_NOT_IDENTIFIABLE_FROM_CURRENT_LOGS"
            reason = "all decisions are deterministic and no exploration support is observed"
        elif overlap == 0.0:
            status = "OPE_NOT_IDENTIFIABLE_FROM_CURRENT_LOGS"
            reason = "action support has no common overlap"
        else:
            status = "SUPPORT_DIAGNOSTIC_POSITIVE_NOT_CAUSAL"
            reason = (
                "decision-time support is present; scientific identifiability remains a "
                "separate audit"
            )
        return SupportAudit(
            len(records),
            stochastic,
            deterministic,
            tuple(sorted(action_counts.items())),
            len({record.shared_resource_digest for record in records}),
            overlap,
            status,
            reason,
        )


__all__ = [
    "SCHEMA_VERSION",
    "DecisionLogRecord",
    "DecisionLogStore",
    "DecisionLoggingPolicy",
    "SupportAudit",
    "canonical_digest",
]
