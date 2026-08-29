"""Versioned, privacy-bounded policy observations for future research runs.

This module records operational observations. It deliberately does not infer a
causal switch cost or fill unavailable measurements with zero.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from itertools import pairwise
from math import isfinite
from pathlib import Path
from typing import Any, Literal

ObservationSchema = Literal["routemind-policy-observation-v1"]
SemanticClass = Literal["OBSERVED", "DERIVED", "SIMULATOR_ONLY", "CONFIGURATION", "MODEL_OUTPUT"]
ComponentStatus = Literal["MEASURED", "DERIVED", "UNAVAILABLE", "NOT_APPLICABLE"]
ClockDomain = Literal["WALL", "SIMULATED", "REPLAY"]

SCHEMA_VERSION: ObservationSchema = "routemind-policy-observation-v1"
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9._:/-]{1,256}$")
_FORBIDDEN_KEYS = re.compile(
    r"(?:secret|password|token|api[_-]?key|authorization|credential|payment|email|phone|address|name)",
    re.IGNORECASE,
)


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _require_id(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip() or not _SAFE_ID.fullmatch(value):
        raise ValueError(f"{field} must be a safe non-empty identifier")


def _finite_number(value: float | int | None, field: str) -> None:
    if value is not None and (not isinstance(value, (int, float)) or not isfinite(float(value))):
        raise ValueError(f"{field} must be finite when present")


@dataclass(frozen=True, slots=True)
class SwitchCostComponent:
    """One auditable consequence component; value is absent when unavailable."""

    name: str
    status: ComponentStatus
    value: float | int | str | None = None
    unit: str | None = None
    provenance: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("cost component name must not be blank")
        if self.status not in {"MEASURED", "DERIVED", "UNAVAILABLE", "NOT_APPLICABLE"}:
            raise ValueError("unsupported cost component status")
        if self.status in {"UNAVAILABLE", "NOT_APPLICABLE"} and self.value is not None:
            raise ValueError("unavailable cost components must not contain a value")
        if self.status in {"MEASURED", "DERIVED"} and self.value is None:
            raise ValueError("measured or derived cost components require a value")
        _finite_number(
            self.value if isinstance(self.value, (int, float)) else None,
            "component value",
        )
        if self.unit is not None and not self.unit.strip():
            raise ValueError("component unit must not be blank when present")

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "value": self.value,
            "unit": self.unit,
            "provenance": self.provenance,
        }


@dataclass(frozen=True, slots=True)
class PolicyObservation:
    run_id: str
    decision_id: str
    request_id: str
    tick: int
    previous_policy: str
    selected_policy: str
    switch_occurred: bool
    switch_reason: str
    selection_mode: str
    policy_version: str
    configuration_digest: str
    deterministic_seed: int | None
    clock_domain: ClockDomain
    state: tuple[tuple[str, Any], ...] = ()
    semantics: tuple[tuple[str, SemanticClass], ...] = ()
    consequences: tuple[SwitchCostComponent, ...] = ()
    provenance: tuple[tuple[str, str], ...] = ()
    scenario_id: str | None = None
    timestamp: str | None = None
    fallback_state: str = "NONE"

    def __post_init__(self) -> None:
        for field, value in (
            ("run_id", self.run_id),
            ("decision_id", self.decision_id),
            ("request_id", self.request_id),
            ("previous_policy", self.previous_policy),
            ("selected_policy", self.selected_policy),
            ("switch_reason", self.switch_reason),
            ("selection_mode", self.selection_mode),
            ("policy_version", self.policy_version),
            ("fallback_state", self.fallback_state),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must not be blank")
        if self.scenario_id is not None:
            _require_id(self.scenario_id, "scenario_id")
        if self.tick < 0:
            raise ValueError("tick must be non-negative")
        if self.switch_occurred != (self.previous_policy != self.selected_policy):
            raise ValueError("switch_occurred must match policy transition")
        if not _DIGEST.fullmatch(self.configuration_digest):
            raise ValueError("configuration_digest must be a lowercase SHA-256 digest")
        if self.deterministic_seed is not None and self.deterministic_seed < 0:
            raise ValueError("deterministic_seed must be non-negative")
        if self.clock_domain not in {"WALL", "SIMULATED", "REPLAY"}:
            raise ValueError("unsupported observation clock domain")
        semantic_keys = {key for key, _ in self.semantics}
        if len(semantic_keys) != len(self.semantics):
            raise ValueError("observation semantic keys must be unique")
        allowed_semantics = {
            "OBSERVED",
            "DERIVED",
            "SIMULATOR_ONLY",
            "CONFIGURATION",
            "MODEL_OUTPUT",
        }
        if any(value not in allowed_semantics for _, value in self.semantics):
            raise ValueError("unsupported semantic class")
        try:
            json.dumps(dict(self.state), ensure_ascii=True, allow_nan=False)
            json.dumps(dict(self.provenance), ensure_ascii=True, allow_nan=False)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "observation state and provenance must be JSON serializable"
            ) from error

    def as_dict(self, *, include_timestamp: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "scenario_id": self.scenario_id,
            "decision_id": self.decision_id,
            "request_id": self.request_id,
            "tick": self.tick,
            "clock_domain": self.clock_domain,
            "previous_policy": self.previous_policy,
            "selected_policy": self.selected_policy,
            "switch_occurred": self.switch_occurred,
            "switch_reason": self.switch_reason,
            "selection_mode": self.selection_mode,
            "policy_version": self.policy_version,
            "configuration_digest": self.configuration_digest,
            "deterministic_seed": self.deterministic_seed,
            "fallback_state": self.fallback_state,
            "state": dict(self.state),
            "semantics": dict(self.semantics),
            "consequences": [component.as_dict() for component in self.consequences],
            "provenance": dict(self.provenance),
            "observation_semantics": "observational_association; not causal_switch_cost",
        }
        if include_timestamp:
            result["timestamp"] = self.timestamp
        return result

    @property
    def replay_digest(self) -> str:
        """Digest deterministic fields only; wall timestamps never affect replay."""

        return canonical_digest(self.as_dict(include_timestamp=False))


@dataclass(frozen=True, slots=True)
class PolicyTraceMetrics:
    decision_count: int
    switch_count: int
    switch_rate: float
    dwell_ticks: tuple[int, ...]
    reversal_count: int
    transition_matrix: tuple[tuple[str, str, int], ...]
    policy_occupancy: tuple[tuple[str, int], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision_count": self.decision_count,
            "switch_count": self.switch_count,
            "switch_rate": self.switch_rate,
            "dwell_ticks": self.dwell_ticks,
            "reversal_count": self.reversal_count,
            "transition_matrix": [
                {"previous_policy": before, "selected_policy": after, "count": count}
                for before, after, count in self.transition_matrix
            ],
            "policy_occupancy": [
                {"policy": policy, "count": count} for policy, count in self.policy_occupancy
            ],
        }


class PolicyTrace:
    """Small in-memory recorder suitable for a run, replay, or bounded export."""

    def __init__(self) -> None:
        self._observations: list[PolicyObservation] = []

    @property
    def observations(self) -> tuple[PolicyObservation, ...]:
        return tuple(self._observations)

    def record(
        self,
        *,
        run_id: str,
        decision_id: str,
        request_id: str,
        tick: int,
        selected_policy: str,
        policy_version: str,
        configuration_digest: str,
        deterministic_seed: int | None = None,
        scenario_id: str | None = None,
        previous_policy: str | None = None,
        switch_reason: str | None = None,
        selection_mode: str = "deterministic",
        clock_domain: ClockDomain = "SIMULATED",
        state: Mapping[str, Any] | None = None,
        semantics: Mapping[str, SemanticClass] | None = None,
        consequences: tuple[SwitchCostComponent, ...] = (),
        provenance: Mapping[str, str] | None = None,
        fallback_state: str = "NONE",
        timestamp: str | None = None,
    ) -> PolicyObservation:
        before = previous_policy or (
            self._observations[-1].selected_policy if self._observations else selected_policy
        )
        switched = before != selected_policy
        observation = PolicyObservation(
            run_id=run_id,
            scenario_id=scenario_id,
            decision_id=decision_id,
            request_id=request_id,
            tick=tick,
            previous_policy=before,
            selected_policy=selected_policy,
            switch_occurred=switched,
            switch_reason=switch_reason or ("policy_switch" if switched else "policy_held"),
            selection_mode=selection_mode,
            policy_version=policy_version,
            configuration_digest=configuration_digest,
            deterministic_seed=deterministic_seed,
            clock_domain=clock_domain,
            state=tuple(sorted((state or {}).items())),
            semantics=tuple(sorted((semantics or {}).items())),
            consequences=consequences,
            provenance=tuple(sorted((provenance or {}).items())),
            fallback_state=fallback_state,
            timestamp=timestamp,
        )
        self._observations.append(observation)
        return observation

    def metrics(self, *, window_ticks: int | None = None) -> PolicyTraceMetrics:
        observations = self._observations
        if window_ticks is not None:
            if window_ticks <= 0:
                raise ValueError("window_ticks must be positive")
            end = observations[-1].tick if observations else 0
            observations = [item for item in observations if item.tick >= end - window_ticks]
        decisions = len(observations)
        switches = sum(item.switch_occurred for item in observations)
        dwell = tuple(
            current.tick - previous.tick
            for previous, current in pairwise(observations)
            if current.switch_occurred
        )
        reversals = sum(
            observations[index - 2].selected_policy == observations[index].selected_policy
            and observations[index - 2].selected_policy != observations[index - 1].selected_policy
            for index in range(2, len(observations))
        )
        transitions: dict[tuple[str, str], int] = {}
        occupancy: dict[str, int] = {}
        for item in observations:
            key = (item.previous_policy, item.selected_policy)
            transitions[key] = transitions.get(key, 0) + 1
            occupancy[item.selected_policy] = occupancy.get(item.selected_policy, 0) + 1
        return PolicyTraceMetrics(
            decisions,
            switches,
            switches / decisions if decisions else 0.0,
            dwell,
            reversals,
            tuple(
                (before, after, transitions[(before, after)])
                for before, after in sorted(transitions)
            ),
            tuple((policy, occupancy[policy]) for policy in sorted(occupancy)),
        )

    def replay_digest(self) -> str:
        return canonical_digest(
            [item.as_dict(include_timestamp=False) for item in self._observations]
        )


@dataclass(frozen=True, slots=True)
class ObservationExport:
    path: Path
    manifest_path: Path
    record_count: int
    sha256: str


class ResearchObservationExporter:
    """Write only bounded observation fields below ROUTEMIND_DATA_ROOT."""

    def __init__(self, root: Path | str | None = None) -> None:
        configured = root if root is not None else os.getenv("ROUTEMIND_DATA_ROOT")
        if not configured:
            raise ValueError("ROUTEMIND_DATA_ROOT must be configured for research observations")
        self.root = Path(configured).expanduser().resolve()

    def export(self, observations: tuple[PolicyObservation, ...]) -> ObservationExport:
        rows = [_redact(item.as_dict()) for item in observations]
        encoded = "".join(
            json.dumps(row, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
            for row in rows
        ).encode("utf-8")
        target = self.root / "research-observations" / "policy-observations-v1.jsonl"
        manifest_path = target.with_name("manifest-v1.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_bytes(encoded)
        os.replace(temporary, target)
        digest = sha256(encoded).hexdigest()
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "format": "jsonl",
            "root_policy": "ROUTEMIND_DATA_ROOT",
            "path": target.relative_to(self.root).as_posix(),
            "record_count": len(rows),
            "sha256": digest,
            "claim_boundary": "observational_association_only",
        }
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return ObservationExport(target, manifest_path, len(rows), digest)


def _redact(value: Any, key: str | None = None) -> Any:
    if key is not None and _FORBIDDEN_KEYS.search(key):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {
            str(item_key): _redact(item_value, str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    return value


__all__ = [
    "SCHEMA_VERSION",
    "ObservationExport",
    "PolicyObservation",
    "PolicyTrace",
    "PolicyTraceMetrics",
    "ResearchObservationExporter",
    "SwitchCostComponent",
    "canonical_digest",
]
