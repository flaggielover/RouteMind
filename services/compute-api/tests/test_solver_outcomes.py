from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from routemind_compute.application.solver_outcomes import (
    IncumbentVerification,
    ResourceLimitKind,
    SolverOutcome,
    SolverProof,
    SolverResourceLimits,
    SolverResourceUsage,
    SolverRunObservation,
    SolverTermination,
    classify_solver_run,
)
from routemind_compute.application.verification import (
    PublicVrptwVerificationReport,
    VerificationIssue,
)

MATRIX_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "research"
    / "r3"
    / "manifests"
    / "solver-outcomes"
    / "solver-outcome-matrix-v1.json"
)


def report(*, valid: bool = True, complete: bool = True) -> PublicVrptwVerificationReport:
    issues = () if valid else (VerificationIssue("invalid_route", "fixture rejection"),)
    return PublicVrptwVerificationReport(valid, issues, ("fixture",), 1, 10.0, complete)


def observation(**overrides: object) -> SolverRunObservation:
    values: dict[str, object] = {
        "run_id": "run-1",
        "solver_name": "reference-solver",
        "solver_version": "1.2.3",
        "termination": SolverTermination.COMPLETED,
        "proof": SolverProof.NONE,
        "usage": SolverResourceUsage(2.0, 100, 50),
        "incumbent_present": True,
        "verification_report": report(),
    }
    values.update(overrides)
    return SolverRunObservation(**values)  # type: ignore[arg-type]


def limits(**overrides: object) -> SolverResourceLimits:
    values: dict[str, object] = {
        "wall_time_seconds": 10.0,
        "memory_bytes": 1_000,
        "node_limit": 500,
        "threads": 1,
    }
    values.update(overrides)
    return SolverResourceLimits(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value, expected",
    [
        (observation(proof=SolverProof.OPTIMALITY), SolverOutcome.OPTIMAL),
        (observation(), SolverOutcome.FEASIBLE_INCUMBENT),
        (
            observation(
                proof=SolverProof.INFEASIBILITY,
                incumbent_present=False,
                verification_report=None,
            ),
            SolverOutcome.INFEASIBLE_PROVEN,
        ),
        (
            observation(termination=SolverTermination.WALL_TIME_LIMIT, proof=SolverProof.NONE),
            SolverOutcome.TIMEOUT_WITH_FEASIBLE,
        ),
        (
            observation(
                termination=SolverTermination.WALL_TIME_LIMIT,
                incumbent_present=False,
                verification_report=None,
            ),
            SolverOutcome.TIMEOUT_NO_FEASIBLE,
        ),
        (
            observation(termination=SolverTermination.MEMORY_LIMIT),
            SolverOutcome.RESOURCE_LIMIT_WITH_FEASIBLE,
        ),
        (
            observation(
                termination=SolverTermination.NODE_LIMIT,
                incumbent_present=False,
                verification_report=None,
            ),
            SolverOutcome.RESOURCE_LIMIT_NO_FEASIBLE,
        ),
        (
            observation(
                termination=SolverTermination.ERROR,
                incumbent_present=False,
                verification_report=None,
                failure_code="solver_crash",
            ),
            SolverOutcome.FAILED,
        ),
        (
            observation(incumbent_present=False, verification_report=None),
            SolverOutcome.FAILED,
        ),
    ],
)
def test_outcome_contract_keeps_all_terminal_states_distinct(
    value: SolverRunObservation, expected: SolverOutcome
) -> None:
    classified = classify_solver_run(value, limits())

    assert classified.outcome is expected
    assert classified.exact is (expected is SolverOutcome.OPTIMAL)
    assert classified.accepted_feasible_incumbent is (
        expected
        in {
            SolverOutcome.OPTIMAL,
            SolverOutcome.FEASIBLE_INCUMBENT,
            SolverOutcome.TIMEOUT_WITH_FEASIBLE,
            SolverOutcome.RESOURCE_LIMIT_WITH_FEASIBLE,
        }
    )


@pytest.mark.parametrize(
    "verification, expected",
    [
        (None, IncumbentVerification.NOT_RUN),
        (report(valid=False), IncumbentVerification.REJECTED),
        (report(complete=False), IncumbentVerification.VERIFIED_PARTIAL),
    ],
)
def test_timeout_never_promotes_unverified_or_incomplete_incumbent(
    verification: PublicVrptwVerificationReport | None,
    expected: IncumbentVerification,
) -> None:
    classified = classify_solver_run(
        observation(
            termination=SolverTermination.WALL_TIME_LIMIT,
            verification_report=verification,
        ),
        limits(),
    )

    assert classified.outcome is SolverOutcome.TIMEOUT_NO_FEASIBLE
    assert classified.verification is expected
    assert classified.accepted_feasible_incumbent is False


def test_report_inconsistency_fails_closed_and_preserves_issue_codes() -> None:
    inconsistent = replace(report(valid=False), valid=True)
    classified = classify_solver_run(
        observation(
            termination=SolverTermination.WALL_TIME_LIMIT,
            verification_report=inconsistent,
        ),
        limits(),
    )

    assert classified.outcome is SolverOutcome.TIMEOUT_NO_FEASIBLE
    assert classified.verification is IncumbentVerification.REJECTED
    assert classified.verification_issue_codes == ("invalid_route",)


@pytest.mark.parametrize(
    "usage, expected, event",
    [
        (
            SolverResourceUsage(10.1, 100, 50),
            SolverOutcome.TIMEOUT_WITH_FEASIBLE,
            ResourceLimitKind.WALL_TIME,
        ),
        (
            SolverResourceUsage(2, 1_001, 50),
            SolverOutcome.RESOURCE_LIMIT_WITH_FEASIBLE,
            ResourceLimitKind.MEMORY,
        ),
        (
            SolverResourceUsage(2, 100, 501),
            SolverOutcome.RESOURCE_LIMIT_WITH_FEASIBLE,
            ResourceLimitKind.SEARCH_NODES,
        ),
    ],
)
def test_observed_resource_breach_is_independent_from_reported_termination(
    usage: SolverResourceUsage,
    expected: SolverOutcome,
    event: ResourceLimitKind,
) -> None:
    classified = classify_solver_run(observation(usage=usage), limits())

    assert classified.termination is SolverTermination.COMPLETED
    assert classified.outcome is expected
    assert event in classified.limit_events


def test_failure_remains_failure_even_when_a_verified_incumbent_exists() -> None:
    classified = classify_solver_run(
        observation(termination=SolverTermination.ERROR, failure_code="backend_error"), limits()
    )

    assert classified.outcome is SolverOutcome.FAILED
    assert classified.verification is IncumbentVerification.VERIFIED_COMPLETE
    assert classified.accepted_feasible_incumbent is False
    assert "failure:backend_error" in classified.reason_codes


def test_classified_payload_is_stable_and_records_limit_lineage() -> None:
    configured = limits()
    first = classify_solver_run(observation(), configured)
    second = classify_solver_run(observation(), configured)

    assert first == second
    assert first.limits_digest == configured.digest
    assert len(first.limits_digest) == 64
    assert first.payload()["outcome"] == "FEASIBLE_INCUMBENT"
    assert first.payload()["verification"] == "VERIFIED_COMPLETE"
    assert configured.payload()["threads"] == 1
    assert observation().usage.payload()["explored_nodes"] == 50


def test_classifier_rejects_untyped_boundary_objects() -> None:
    with pytest.raises(ValueError, match="observation"):
        classify_solver_run(object(), limits())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="limits"):
        classify_solver_run(observation(), object())  # type: ignore[arg-type]


def test_frozen_solver_outcome_matrix_replays_without_collapsing_states() -> None:
    manifest = cast(dict[str, object], json.loads(MATRIX_PATH.read_text(encoding="utf-8")))
    assert manifest["schema_version"] == "solver-outcome-matrix-v1"
    assert manifest["contract_version"] == "solver-outcome-contract-v1"
    configured = SolverResourceLimits(**cast(dict[str, object], manifest["limits"]))  # type: ignore[arg-type]
    cases = cast(list[dict[str, object]], manifest["cases"])
    assert len(cases) == 17
    assert len({item["id"] for item in cases}) == len(cases)

    observed_outcomes: set[SolverOutcome] = set()
    for item in cases:
        verification_name = cast(str, item["verification"])
        verification = {
            "NOT_PRESENT": None,
            "NOT_RUN": None,
            "REJECTED": report(valid=False),
            "VERIFIED_PARTIAL": report(complete=False),
            "VERIFIED_COMPLETE": report(),
        }[verification_name]
        elapsed, memory, nodes = cast(list[float | int], item["usage"])
        value = SolverRunObservation(
            run_id=cast(str, item["id"]),
            solver_name="matrix-fixture",
            solver_version="1.0.0",
            termination=SolverTermination(cast(str, item["termination"])),
            proof=SolverProof(cast(str, item["proof"])),
            usage=SolverResourceUsage(float(elapsed), int(memory), int(nodes)),
            incumbent_present=cast(bool, item["incumbent"]),
            verification_report=verification,
            failure_code=cast(str | None, item.get("failure_code")),
        )
        classified = classify_solver_run(value, configured)
        expected = SolverOutcome(cast(str, item["expected"]))
        assert classified.outcome is expected, item["id"]
        assert classified.accepted_feasible_incumbent is item["accepted"], item["id"]
        observed_outcomes.add(classified.outcome)

    assert observed_outcomes == set(SolverOutcome)


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"wall_time_seconds": 0}, "wall_time_seconds"),
        ({"wall_time_seconds": float("nan")}, "wall_time_seconds"),
        ({"memory_bytes": 0}, "memory_bytes"),
        ({"node_limit": True}, "node_limit"),
        ({"threads": 0}, "threads"),
    ],
)
def test_resource_limits_fail_closed(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        limits(**overrides)


@pytest.mark.parametrize(
    "usage, message",
    [
        (lambda: SolverResourceUsage(-1), "elapsed_seconds"),
        (lambda: SolverResourceUsage(float("inf")), "elapsed_seconds"),
        (lambda: SolverResourceUsage(1, -1), "peak_memory_bytes"),
        (lambda: SolverResourceUsage(1, explored_nodes=True), "explored_nodes"),
    ],
)
def test_resource_usage_fails_closed(usage: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        usage()  # type: ignore[operator]


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"run_id": " "}, "identity"),
        ({"solver_name": 1}, "identity"),
        ({"termination": "COMPLETED"}, "termination"),
        ({"proof": "NONE"}, "proof"),
        ({"usage": None}, "usage"),
        ({"incumbent_present": 1}, "incumbent_present"),
        ({"verification_report": object()}, "verification_report"),
        (
            {"incumbent_present": False, "verification_report": report()},
            "verification report",
        ),
        ({"proof": SolverProof.INFEASIBILITY}, "infeasibility proof"),
        (
            {
                "termination": SolverTermination.WALL_TIME_LIMIT,
                "proof": SolverProof.OPTIMALITY,
            },
            "proof requires",
        ),
        (
            {
                "termination": SolverTermination.ERROR,
                "incumbent_present": False,
                "verification_report": None,
            },
            "failure_code",
        ),
        ({"failure_code": " "}, "failure_code"),
        ({"failure_code": 1}, "failure_code"),
    ],
)
def test_run_observation_rejects_contradictory_or_untyped_state(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        observation(**overrides)
