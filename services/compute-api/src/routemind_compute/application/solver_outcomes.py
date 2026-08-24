from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from math import isfinite

from routemind_compute.application.verification import PublicVrptwVerificationReport


class SolverOutcome(StrEnum):
    OPTIMAL = "OPTIMAL"
    FEASIBLE_INCUMBENT = "FEASIBLE_INCUMBENT"
    INFEASIBLE_PROVEN = "INFEASIBLE_PROVEN"
    TIMEOUT_WITH_FEASIBLE = "TIMEOUT_WITH_FEASIBLE"
    TIMEOUT_NO_FEASIBLE = "TIMEOUT_NO_FEASIBLE"
    RESOURCE_LIMIT_WITH_FEASIBLE = "RESOURCE_LIMIT_WITH_FEASIBLE"
    RESOURCE_LIMIT_NO_FEASIBLE = "RESOURCE_LIMIT_NO_FEASIBLE"
    FAILED = "FAILED"


class SolverTermination(StrEnum):
    COMPLETED = "COMPLETED"
    WALL_TIME_LIMIT = "WALL_TIME_LIMIT"
    MEMORY_LIMIT = "MEMORY_LIMIT"
    NODE_LIMIT = "NODE_LIMIT"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"


class SolverProof(StrEnum):
    NONE = "NONE"
    OPTIMALITY = "OPTIMALITY"
    INFEASIBILITY = "INFEASIBILITY"


class IncumbentVerification(StrEnum):
    NOT_PRESENT = "NOT_PRESENT"
    NOT_RUN = "NOT_RUN"
    VERIFIED_COMPLETE = "VERIFIED_COMPLETE"
    VERIFIED_PARTIAL = "VERIFIED_PARTIAL"
    REJECTED = "REJECTED"


class ResourceLimitKind(StrEnum):
    WALL_TIME = "WALL_TIME"
    MEMORY = "MEMORY"
    SEARCH_NODES = "SEARCH_NODES"


def _finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def _positive_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _non_negative_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


@dataclass(frozen=True, slots=True)
class SolverResourceLimits:
    wall_time_seconds: float
    memory_bytes: int | None = None
    node_limit: int | None = None
    threads: int = 1

    def __post_init__(self) -> None:
        if not _finite_number(self.wall_time_seconds) or self.wall_time_seconds <= 0:
            raise ValueError("wall_time_seconds must be finite and positive")
        if self.memory_bytes is not None and not _positive_integer(self.memory_bytes):
            raise ValueError("memory_bytes must be a positive integer when present")
        if self.node_limit is not None and not _positive_integer(self.node_limit):
            raise ValueError("node_limit must be a positive integer when present")
        if not _positive_integer(self.threads):
            raise ValueError("threads must be a positive integer")

    def payload(self) -> dict[str, object]:
        return {
            "wall_time_seconds": self.wall_time_seconds,
            "memory_bytes": self.memory_bytes,
            "node_limit": self.node_limit,
            "threads": self.threads,
        }

    @property
    def digest(self) -> str:
        encoded = json.dumps(
            self.payload(), sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        return sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class SolverResourceUsage:
    elapsed_seconds: float
    peak_memory_bytes: int | None = None
    explored_nodes: int | None = None

    def __post_init__(self) -> None:
        if not _finite_number(self.elapsed_seconds) or self.elapsed_seconds < 0:
            raise ValueError("elapsed_seconds must be finite and non-negative")
        if self.peak_memory_bytes is not None and not _non_negative_integer(self.peak_memory_bytes):
            raise ValueError("peak_memory_bytes must be a non-negative integer when present")
        if self.explored_nodes is not None and not _non_negative_integer(self.explored_nodes):
            raise ValueError("explored_nodes must be a non-negative integer when present")

    def payload(self) -> dict[str, object]:
        return {
            "elapsed_seconds": self.elapsed_seconds,
            "peak_memory_bytes": self.peak_memory_bytes,
            "explored_nodes": self.explored_nodes,
        }


@dataclass(frozen=True, slots=True)
class SolverRunObservation:
    run_id: str
    solver_name: str
    solver_version: str
    termination: SolverTermination
    proof: SolverProof
    usage: SolverResourceUsage
    incumbent_present: bool
    verification_report: PublicVrptwVerificationReport | None = None
    failure_code: str | None = None

    def __post_init__(self) -> None:
        identities = (self.run_id, self.solver_name, self.solver_version)
        if any(not isinstance(value, str) or not value.strip() for value in identities):
            raise ValueError("run and solver identity must not be blank")
        if not isinstance(self.termination, SolverTermination):
            raise ValueError("termination must be a SolverTermination")
        if not isinstance(self.proof, SolverProof):
            raise ValueError("proof must be a SolverProof")
        if not isinstance(self.usage, SolverResourceUsage):
            raise ValueError("usage must be SolverResourceUsage")
        if not isinstance(self.incumbent_present, bool):
            raise ValueError("incumbent_present must be boolean")
        if self.verification_report is not None and not isinstance(
            self.verification_report, PublicVrptwVerificationReport
        ):
            raise ValueError("verification_report must be a public VRPTW verification report")
        if self.verification_report is not None and not self.incumbent_present:
            raise ValueError("verification report requires an incumbent")
        if self.proof is SolverProof.INFEASIBILITY and self.incumbent_present:
            raise ValueError("infeasibility proof cannot accompany an incumbent")
        if (
            self.proof is not SolverProof.NONE
            and self.termination is not SolverTermination.COMPLETED
        ):
            raise ValueError("proof requires completed solver termination")
        if self.termination is SolverTermination.ERROR and not self.failure_code:
            raise ValueError("error termination requires a failure_code")
        if self.failure_code is not None and (
            not isinstance(self.failure_code, str) or not self.failure_code.strip()
        ):
            raise ValueError("failure_code must not be blank when present")


@dataclass(frozen=True, slots=True)
class ClassifiedSolverRun:
    run_id: str
    outcome: SolverOutcome
    termination: SolverTermination
    proof: SolverProof
    verification: IncumbentVerification
    limit_events: tuple[ResourceLimitKind, ...]
    accepted_feasible_incumbent: bool
    exact: bool
    limits_digest: str
    reason_codes: tuple[str, ...]
    verification_issue_codes: tuple[str, ...]

    def payload(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "outcome": self.outcome.value,
            "termination": self.termination.value,
            "proof": self.proof.value,
            "verification": self.verification.value,
            "limit_events": [item.value for item in self.limit_events],
            "accepted_feasible_incumbent": self.accepted_feasible_incumbent,
            "exact": self.exact,
            "limits_digest": self.limits_digest,
            "reason_codes": list(self.reason_codes),
            "verification_issue_codes": list(self.verification_issue_codes),
        }


def classify_solver_run(
    observation: SolverRunObservation, limits: SolverResourceLimits
) -> ClassifiedSolverRun:
    if not isinstance(observation, SolverRunObservation):
        raise ValueError("observation must be SolverRunObservation")
    if not isinstance(limits, SolverResourceLimits):
        raise ValueError("limits must be SolverResourceLimits")
    verification = _verification_status(observation)
    verified_complete = verification is IncumbentVerification.VERIFIED_COMPLETE
    limit_events = _limit_events(observation, limits)
    outcome = _outcome(observation, verified_complete, limit_events)
    accepted = verified_complete and outcome is not SolverOutcome.FAILED
    reasons = [f"termination:{observation.termination.value}"]
    reasons.append(f"proof:{observation.proof.value}")
    reasons.append(f"verification:{verification.value}")
    reasons.extend(f"limit:{item.value}" for item in limit_events)
    if observation.failure_code:
        reasons.append(f"failure:{observation.failure_code}")
    report = observation.verification_report
    issue_codes = () if report is None else tuple(sorted({item.code for item in report.issues}))
    return ClassifiedSolverRun(
        run_id=observation.run_id,
        outcome=outcome,
        termination=observation.termination,
        proof=observation.proof,
        verification=verification,
        limit_events=limit_events,
        accepted_feasible_incumbent=accepted,
        exact=outcome is SolverOutcome.OPTIMAL,
        limits_digest=limits.digest,
        reason_codes=tuple(reasons),
        verification_issue_codes=issue_codes,
    )


def _verification_status(observation: SolverRunObservation) -> IncumbentVerification:
    if not observation.incumbent_present:
        return IncumbentVerification.NOT_PRESENT
    report = observation.verification_report
    if report is None:
        return IncumbentVerification.NOT_RUN
    if report.valid != (not report.issues):
        return IncumbentVerification.REJECTED
    if not report.valid:
        return IncumbentVerification.REJECTED
    if report.complete:
        return IncumbentVerification.VERIFIED_COMPLETE
    return IncumbentVerification.VERIFIED_PARTIAL


def _limit_events(
    observation: SolverRunObservation, limits: SolverResourceLimits
) -> tuple[ResourceLimitKind, ...]:
    events: set[ResourceLimitKind] = set()
    if (
        observation.termination is SolverTermination.WALL_TIME_LIMIT
        or observation.usage.elapsed_seconds > limits.wall_time_seconds
    ):
        events.add(ResourceLimitKind.WALL_TIME)
    if observation.termination is SolverTermination.MEMORY_LIMIT or (
        limits.memory_bytes is not None
        and observation.usage.peak_memory_bytes is not None
        and observation.usage.peak_memory_bytes > limits.memory_bytes
    ):
        events.add(ResourceLimitKind.MEMORY)
    if observation.termination is SolverTermination.NODE_LIMIT or (
        limits.node_limit is not None
        and observation.usage.explored_nodes is not None
        and observation.usage.explored_nodes > limits.node_limit
    ):
        events.add(ResourceLimitKind.SEARCH_NODES)
    return tuple(sorted(events, key=lambda item: item.value))


def _outcome(
    observation: SolverRunObservation,
    accepted: bool,
    limit_events: tuple[ResourceLimitKind, ...],
) -> SolverOutcome:
    if observation.termination in {SolverTermination.ERROR, SolverTermination.CANCELLED}:
        return SolverOutcome.FAILED
    if ResourceLimitKind.WALL_TIME in limit_events:
        return (
            SolverOutcome.TIMEOUT_WITH_FEASIBLE if accepted else SolverOutcome.TIMEOUT_NO_FEASIBLE
        )
    if limit_events:
        return (
            SolverOutcome.RESOURCE_LIMIT_WITH_FEASIBLE
            if accepted
            else SolverOutcome.RESOURCE_LIMIT_NO_FEASIBLE
        )
    if observation.proof is SolverProof.INFEASIBILITY:
        return SolverOutcome.INFEASIBLE_PROVEN
    if accepted and observation.proof is SolverProof.OPTIMALITY:
        return SolverOutcome.OPTIMAL
    if accepted:
        return SolverOutcome.FEASIBLE_INCUMBENT
    return SolverOutcome.FAILED
