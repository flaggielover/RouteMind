"""Bounded, manifest-first orchestration for local and future experiments.

The scheduler is deliberately small: it owns admission, resource limits,
timeouts, cancellation, and audit lineage. It never owns dispatch authority and
it never writes frozen evidence. A caller supplies the already frozen manifest
and a pure/bounded operation; external execution remains a separate gate.
"""

from __future__ import annotations

import json
import re
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Literal

SchedulerStatus = Literal["COMPLETED", "TIMED_OUT", "CANCELLED", "REJECTED", "FAILED"]
Operation = Callable[[threading.Event], Any]
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9._:/-]{1,128}$")


def canonical_digest(value: Any) -> str:
    return sha256(
        json.dumps(
            value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{name} must be a safe non-empty identifier")
    return value


@dataclass(frozen=True, slots=True)
class ExperimentManifest:
    """Immutable admission request for one bounded experiment run."""

    manifest_id: str
    code_revision: str
    scenario_id: str
    resource_units: int
    concurrency: int
    timeout_seconds: float
    lineage: tuple[str, ...]
    manifest_digest: str
    evidence_targets: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value, name in (
            (self.manifest_id, "manifest_id"),
            (self.code_revision, "code_revision"),
            (self.scenario_id, "scenario_id"),
        ):
            _text(value, name)
        if self.resource_units <= 0:
            raise ValueError("resource_units must be positive")
        if self.concurrency <= 0:
            raise ValueError("concurrency must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if not self.lineage or any(not item.strip() for item in self.lineage):
            raise ValueError("lineage must contain at least one non-blank item")
        if len(set(self.lineage)) != len(self.lineage):
            raise ValueError("lineage entries must be unique")
        if not _DIGEST.fullmatch(self.manifest_digest):
            raise ValueError("manifest_digest must be a lowercase SHA-256 digest")
        if len(set(self.evidence_targets)) != len(self.evidence_targets):
            raise ValueError("evidence_targets must be unique")
        if any(not item.strip() for item in self.evidence_targets):
            raise ValueError("evidence_targets must not contain blank paths")
        if self.manifest_digest != canonical_digest(self.canonical_payload()):
            raise ValueError("manifest_digest does not match the frozen manifest")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "manifest_id": self.manifest_id,
            "code_revision": self.code_revision,
            "scenario_id": self.scenario_id,
            "resource_units": self.resource_units,
            "concurrency": self.concurrency,
            "timeout_seconds": self.timeout_seconds,
            "lineage": self.lineage,
            "evidence_targets": self.evidence_targets,
        }

    @classmethod
    def create(
        cls,
        *,
        manifest_id: str,
        code_revision: str,
        scenario_id: str,
        resource_units: int,
        concurrency: int,
        timeout_seconds: float,
        lineage: tuple[str, ...],
        evidence_targets: tuple[str, ...] = (),
    ) -> ExperimentManifest:
        payload = {
            "manifest_id": manifest_id,
            "code_revision": code_revision,
            "scenario_id": scenario_id,
            "resource_units": resource_units,
            "concurrency": concurrency,
            "timeout_seconds": timeout_seconds,
            "lineage": lineage,
            "evidence_targets": evidence_targets,
        }
        return cls(
            manifest_id,
            code_revision,
            scenario_id,
            resource_units,
            concurrency,
            timeout_seconds,
            lineage,
            canonical_digest(payload),
            evidence_targets,
        )


@dataclass(frozen=True, slots=True)
class SchedulerPolicy:
    max_resource_units: int = 8
    max_concurrency: int = 1
    max_timeout_seconds: float = 300.0

    def __post_init__(self) -> None:
        if self.max_resource_units <= 0 or self.max_concurrency <= 0:
            raise ValueError("scheduler limits must be positive")
        if self.max_timeout_seconds <= 0:
            raise ValueError("max_timeout_seconds must be positive")


@dataclass(frozen=True, slots=True)
class ScheduleAudit:
    job_id: str
    sequence: int
    manifest_id: str
    manifest_digest: str
    status: SchedulerStatus
    reason: str
    lineage_digest: str
    output_digest: str | None = None
    elapsed_ms: int = 0


class ExperimentScheduler:
    """Execute only admitted, bounded operations and retain immutable audits."""

    def __init__(
        self,
        policy: SchedulerPolicy | None = None,
        *,
        frozen_evidence: Mapping[str, str] | None = None,
    ) -> None:
        self.policy = policy or SchedulerPolicy()
        self.frozen_evidence = dict(frozen_evidence or {})
        if any(not _DIGEST.fullmatch(value) for value in self.frozen_evidence.values()):
            raise ValueError("frozen evidence digests must be lowercase SHA-256 values")
        self._lock = threading.Lock()
        self._active = 0
        self._sequence = 0
        self._audits: list[ScheduleAudit] = []

    @property
    def audits(self) -> tuple[ScheduleAudit, ...]:
        return tuple(self._audits)

    def run(
        self,
        manifest: ExperimentManifest,
        operation: Operation,
        *,
        cancel_event: threading.Event | None = None,
    ) -> ScheduleAudit:
        """Run one operation, returning a terminal audit even on rejection."""

        selected_cancel = cancel_event or threading.Event()
        rejection = self._admission_reason(manifest)
        if rejection is not None:
            return self._record(manifest, "REJECTED", rejection, None, 0)
        if selected_cancel.is_set():
            return self._record(manifest, "CANCELLED", "cancelled_before_start", None, 0)

        with self._lock:
            if self._active >= self.policy.max_concurrency:
                over_capacity = True
            else:
                over_capacity = False
                self._active += 1
        if over_capacity:
            return self._record(manifest, "REJECTED", "concurrency_limit_exceeded", None, 0)
        started = time.monotonic()
        holder: dict[str, Any] = {}

        def invoke() -> None:
            try:
                holder["output"] = operation(selected_cancel)
            except BaseException as error:  # retain failure without escaping the audit boundary
                holder["error"] = error

        worker = threading.Thread(
            target=invoke, name=f"routemind-experiment-{manifest.manifest_id}", daemon=True
        )
        worker.start()
        worker.join(manifest.timeout_seconds)
        elapsed_ms = round((time.monotonic() - started) * 1000)
        try:
            if worker.is_alive():
                selected_cancel.set()
                return self._record(manifest, "TIMED_OUT", "timeout_exceeded", None, elapsed_ms)
            if selected_cancel.is_set():
                return self._record(manifest, "CANCELLED", "cancelled", None, elapsed_ms)
            if "error" in holder:
                return self._record(manifest, "FAILED", "operation_failed", None, elapsed_ms)
            try:
                output_digest = canonical_digest(holder.get("output"))
            except (TypeError, ValueError):
                return self._record(manifest, "FAILED", "output_not_digestible", None, elapsed_ms)
            return self._record(manifest, "COMPLETED", "ok", output_digest, elapsed_ms)
        finally:
            with self._lock:
                self._active -= 1

    def _admission_reason(self, manifest: ExperimentManifest) -> str | None:
        if manifest.resource_units > self.policy.max_resource_units:
            return "resource_limit_exceeded"
        if manifest.concurrency > self.policy.max_concurrency:
            return "manifest_concurrency_exceeded"
        if manifest.timeout_seconds > self.policy.max_timeout_seconds:
            return "timeout_limit_exceeded"
        if any(target in self.frozen_evidence for target in manifest.evidence_targets):
            return "frozen_evidence_target_forbidden"
        return None

    def _record(
        self,
        manifest: ExperimentManifest,
        status: SchedulerStatus,
        reason: str,
        output_digest: str | None,
        elapsed_ms: int,
    ) -> ScheduleAudit:
        with self._lock:
            self._sequence += 1
            sequence = self._sequence
            audit = ScheduleAudit(
                f"{manifest.manifest_id}-{sequence:04d}",
                sequence,
                manifest.manifest_id,
                manifest.manifest_digest,
                status,
                reason,
                canonical_digest(
                    {"manifest": manifest.manifest_digest, "lineage": manifest.lineage}
                ),
                output_digest,
                elapsed_ms,
            )
            self._audits.append(audit)
            return audit


__all__ = [
    "ExperimentManifest",
    "ExperimentScheduler",
    "ScheduleAudit",
    "SchedulerPolicy",
    "SchedulerStatus",
    "canonical_digest",
]
