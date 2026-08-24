"""Frozen all-outcome benchmark gap analysis for R3-316."""

from __future__ import annotations

import argparse
import json
import platform
import re
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from math import isclose, isfinite
from pathlib import Path, PurePosixPath
from statistics import median
from typing import cast

_SCHEMA = "routemind-benchmark-gap-analysis-manifest-v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REVISION = re.compile(r"^[0-9a-f]{40}$")
_TASK_ORDER = ("R3-311", "R3-312", "R3-315")
_SOURCE_TASKS = ("R3-311", "R3-312")
_OUTCOMES = (
    "OPTIMAL",
    "FEASIBLE_INCUMBENT",
    "INFEASIBLE_PROVEN",
    "TIMEOUT_WITH_FEASIBLE",
    "TIMEOUT_NO_FEASIBLE",
    "RESOURCE_LIMIT_WITH_FEASIBLE",
    "RESOURCE_LIMIT_NO_FEASIBLE",
    "FAILED",
)
_INCUMBENT_OUTCOMES = {
    "OPTIMAL",
    "FEASIBLE_INCUMBENT",
    "TIMEOUT_WITH_FEASIBLE",
    "RESOURCE_LIMIT_WITH_FEASIBLE",
}
_REFERENCE_STATUSES = (
    "COMPARABLE_SAME_VEHICLE_COUNT",
    "VEHICLE_COUNT_WORSE",
    "VEHICLE_COUNT_BETTER",
    "REFERENCE_QUALITY_REVIEW",
    "REFERENCE_GAP_NOT_APPLICABLE",
)
_VEHICLE_GAP_ALLOWED = {
    "COMPARABLE_SAME_VEHICLE_COUNT",
    "VEHICLE_COUNT_WORSE",
    "VEHICLE_COUNT_BETTER",
}


class BenchmarkGapAnalysisError(ValueError):
    """Raised when a frozen R3-316 analysis invariant is violated."""


@dataclass(frozen=True, slots=True)
class FrozenGapInput:
    task_id: str
    relative_path: str
    sha256: str
    schema_version: str
    manifest_id: str
    selected: int
    retained: int
    analysis_domain: str


@dataclass(frozen=True, slots=True)
class GapAnalysisProtocol:
    manifest_id: str
    manifest_sha256: str
    frozen_against_revision: str
    inputs: tuple[FrozenGapInput, ...]
    source_expected_records: int
    exact_expected_records: int
    ledger_expected_records: int
    result_relative_root: str

    def input_for(self, task_id: str) -> FrozenGapInput:
        matches = [item for item in self.inputs if item.task_id == task_id]
        if len(matches) != 1:
            raise BenchmarkGapAnalysisError(f"input {task_id} is not uniquely frozen")
        return matches[0]


@dataclass(frozen=True, slots=True)
class SourceGapRecord:
    task_id: str
    instance_id: str
    outcome: str
    accepted_verified_complete: bool
    comparison: str
    vehicles: int | None
    reference_vehicles: int
    vehicle_gap_percent: float | None
    distance_gap_percent: float | None
    vehicle_gap_omission: str | None
    distance_gap_omission: str | None

    def payload(self) -> dict[str, object]:
        return {
            "record_id": f"{self.task_id}:{self.instance_id}",
            "task_id": self.task_id,
            "instance_id": self.instance_id,
            "analysis_domain": "SOURCE_DOUBLE_BKS",
            "outcome": self.outcome,
            "accepted_verified_complete": self.accepted_verified_complete,
            "reference_comparison": self.comparison,
            "vehicles": self.vehicles,
            "reference_vehicles": self.reference_vehicles,
            "vehicle_gap_percent": self.vehicle_gap_percent,
            "same_vehicle_distance_gap_percent": self.distance_gap_percent,
            "vehicle_gap_omission": self.vehicle_gap_omission,
            "distance_gap_omission": self.distance_gap_omission,
        }


@dataclass(frozen=True, slots=True)
class ExactGapRecord:
    task_id: str
    source_instance_id: str
    derived_instance_id: str
    exact_status: str
    candidate_status: str
    transformed_gap_percent: float
    artifact_name: str
    artifact_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "record_id": f"{self.task_id}:{self.derived_instance_id}",
            "task_id": self.task_id,
            "source_instance_id": self.source_instance_id,
            "instance_id": self.derived_instance_id,
            "analysis_domain": "DERIVED_CONSERVATIVE_INTEGER_OPTIMUM",
            "outcome": "R3_317_NOT_APPLICABLE",
            "exact_status": self.exact_status,
            "candidate_status": self.candidate_status,
            "transformed_exact_gap_percent": self.transformed_gap_percent,
            "artifact": {"name": self.artifact_name, "sha256": self.artifact_sha256},
        }


def load_gap_analysis_protocol(path: Path) -> GapAnalysisProtocol:
    try:
        raw = path.read_bytes()
        root = _mapping(json.loads(raw), "protocol")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BenchmarkGapAnalysisError("gap analysis protocol is unreadable") from exc
    if _string(root, "schema_version") != _SCHEMA:
        raise BenchmarkGapAnalysisError("gap analysis protocol schema is unsupported")
    if _string(root, "task_id") != "R3-316":
        raise BenchmarkGapAnalysisError("gap analysis task identity must be R3-316")
    if _boolean(root, "material_execution_started"):
        raise BenchmarkGapAnalysisError("frozen analysis plan must precede material execution")
    revision = _string(root, "frozen_against_revision")
    if not _REVISION.fullmatch(revision):
        raise BenchmarkGapAnalysisError("frozen revision must be a full lowercase Git SHA")

    frozen_inputs = tuple(
        _frozen_input(_mapping(item, "frozen input"))
        for item in _sequence(_required(root, "inputs"), "inputs")
    )
    if tuple(item.task_id for item in frozen_inputs) != _TASK_ORDER:
        raise BenchmarkGapAnalysisError("frozen inputs must preserve R3-311/R3-312/R3-315 order")
    if tuple(item.selected for item in frozen_inputs) != (6, 30, 6):
        raise BenchmarkGapAnalysisError("frozen input selections must be 6/30/6")
    if any(item.selected != item.retained for item in frozen_inputs):
        raise BenchmarkGapAnalysisError("every frozen input must retain every selection")
    if tuple(item.analysis_domain for item in frozen_inputs) != (
        "SOURCE_DOUBLE_BKS",
        "SOURCE_DOUBLE_BKS",
        "DERIVED_CONSERVATIVE_INTEGER_OPTIMUM",
    ):
        raise BenchmarkGapAnalysisError("frozen input analysis domains are invalid")

    universes = _mapping(_required(root, "analysis_universes"), "analysis_universes")
    source = _mapping(_required(universes, "source_double_bks"), "source_double_bks")
    exact = _mapping(
        _required(universes, "derived_conservative_integer_optimum"),
        "derived_conservative_integer_optimum",
    )
    ledger = _mapping(_required(universes, "all_outcome_ledger"), "all_outcome_ledger")
    if tuple(_string_array(source, "task_ids")) != _SOURCE_TASKS:
        raise BenchmarkGapAnalysisError("source analysis universe must contain R3-311 and R3-312")
    if tuple(_string_array(exact, "task_ids")) != ("R3-315",):
        raise BenchmarkGapAnalysisError("exact analysis universe must contain only R3-315")
    if tuple(_string_array(ledger, "task_ids")) != _TASK_ORDER:
        raise BenchmarkGapAnalysisError("all-outcome ledger must contain all three inputs")
    source_count = _positive_integer(source, "expected_records")
    exact_count = _positive_integer(exact, "expected_records")
    ledger_count = _positive_integer(ledger, "expected_records")
    if (source_count, exact_count, ledger_count) != (36, 6, 42):
        raise BenchmarkGapAnalysisError("frozen analysis universes must contain 36/6/42 records")

    objective = _mapping(_required(root, "objective_semantics"), "objective_semantics")
    if _string(objective, "source") != "HIERARCHICAL_VEHICLES_THEN_DISTANCE":
        raise BenchmarkGapAnalysisError("source objective must remain hierarchical")
    if _string(objective, "direction") != (
        "Negative is better, zero is equal, and positive is worse for every numeric gap "
        "distribution."
    ):
        raise BenchmarkGapAnalysisError("numeric gap direction differs from the frozen plan")
    eligibility = _mapping(_required(root, "reference_eligibility"), "reference_eligibility")
    for status in _REFERENCE_STATUSES:
        rule = _mapping(_required(eligibility, status), f"reference_eligibility.{status}")
        expected_vehicle = status in _VEHICLE_GAP_ALLOWED
        expected_distance = status == "COMPARABLE_SAME_VEHICLE_COUNT"
        if _boolean(rule, "vehicle_gap_allowed") is not expected_vehicle:
            raise BenchmarkGapAnalysisError(f"vehicle eligibility drifted for {status}")
        if _boolean(rule, "distance_gap_allowed") is not expected_distance:
            raise BenchmarkGapAnalysisError(f"distance eligibility drifted for {status}")

    statistics = _mapping(_required(root, "descriptive_statistics"), "statistics")
    if tuple(_string_array(statistics, "fields")) != (
        "n",
        "minimum",
        "median",
        "p90",
        "maximum",
    ):
        raise BenchmarkGapAnalysisError("descriptive fields differ from the frozen plan")
    if "Type 7" not in _string(statistics, "percentile_method"):
        raise BenchmarkGapAnalysisError("p90 must use the frozen Type 7 method")
    accounting = _mapping(_required(root, "outcome_accounting"), "outcome_accounting")
    if tuple(_string_array(accounting, "r3_317_outcomes")) != _OUTCOMES:
        raise BenchmarkGapAnalysisError("R3-317 outcome accounting is incomplete")

    artifact_policy = _mapping(_required(root, "artifact_policy"), "artifact_policy")
    result_root = _safe_relative_path(artifact_policy, "external_result_relative_root")
    if result_root != "experiments/r3/R3-316":
        raise BenchmarkGapAnalysisError("R3-316 result root differs from the frozen boundary")
    execution = _mapping(_required(root, "execution_policy"), "execution_policy")
    if _integer(execution, "threads") != 1 or _number(execution, "external_cost_usd") != 0:
        raise BenchmarkGapAnalysisError("R3-316 must remain one-thread and zero-cost")

    return GapAnalysisProtocol(
        manifest_id=_string(root, "manifest_id"),
        manifest_sha256=sha256(raw).hexdigest(),
        frozen_against_revision=revision,
        inputs=frozen_inputs,
        source_expected_records=source_count,
        exact_expected_records=exact_count,
        ledger_expected_records=ledger_count,
        result_relative_root=result_root,
    )


def analyze_frozen_results(
    protocol: GapAnalysisProtocol,
    repository_root: Path,
    data_root: Path,
    campaign_id: str,
    code_revision: str,
    implementation_ci_run: int,
) -> dict[str, object]:
    if not campaign_id.strip():
        raise BenchmarkGapAnalysisError("campaign id must not be blank")
    if not _REVISION.fullmatch(code_revision):
        raise BenchmarkGapAnalysisError("code revision must be a full lowercase Git SHA")
    if implementation_ci_run <= 0:
        raise BenchmarkGapAnalysisError("implementation CI run must be positive")
    repository = repository_root.expanduser().resolve()
    data = data_root.expanduser().resolve()
    summaries = {item.task_id: _load_frozen_summary(item, repository) for item in protocol.inputs}
    source_records = tuple(
        record
        for task_id in _SOURCE_TASKS
        for record in _source_records(protocol.input_for(task_id), summaries[task_id])
    )
    exact_records = _exact_records(protocol.input_for("R3-315"), summaries["R3-315"], data)
    if len(source_records) != protocol.source_expected_records:
        raise BenchmarkGapAnalysisError("source record count differs from the frozen universe")
    if len(exact_records) != protocol.exact_expected_records:
        raise BenchmarkGapAnalysisError("exact record count differs from the frozen universe")
    record_ids = [
        *(f"{item.task_id}:{item.instance_id}" for item in source_records),
        *(f"{item.task_id}:{item.derived_instance_id}" for item in exact_records),
    ]
    if len(record_ids) != protocol.ledger_expected_records or len(set(record_ids)) != len(
        record_ids
    ):
        raise BenchmarkGapAnalysisError("all-outcome ledger is incomplete or non-unique")

    by_task = {
        task_id: _source_summary(tuple(item for item in source_records if item.task_id == task_id))
        for task_id in _SOURCE_TASKS
    }
    combined = _source_summary(source_records)
    exact_gaps = tuple(item.transformed_gap_percent for item in exact_records)
    return {
        "schema_version": "routemind-benchmark-gap-analysis-result-v1",
        "task_id": "R3-316",
        "manifest_id": protocol.manifest_id,
        "manifest_sha256": protocol.manifest_sha256,
        "campaign_id": campaign_id,
        "code_revision": code_revision,
        "implementation_ci_run": implementation_ci_run,
        "completed_at_utc": _utc_now(),
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "inputs": [
            {
                "task_id": item.task_id,
                "path": item.relative_path,
                "sha256": item.sha256,
                "selected": item.selected,
                "retained": item.retained,
                "analysis_domain": item.analysis_domain,
            }
            for item in protocol.inputs
        ],
        "audit": {
            "input_files": 3,
            "upstream_records": len(record_ids),
            "accounted_records": len(record_ids),
            "excluded_records": 0,
            "source_double_bks_records": len(source_records),
            "derived_exact_records": len(exact_records),
            "verified_external_exact_artifacts": len(exact_records),
            "duplicate_record_ids": 0,
            "errors": 0,
        },
        "source_double_bks": {"by_task": by_task, "combined": combined},
        "derived_conservative_integer_optimum": {
            "records": len(exact_records),
            "exact_statuses": dict(
                sorted(Counter(item.exact_status for item in exact_records).items())
            ),
            "candidate_statuses": dict(
                sorted(Counter(item.candidate_status for item in exact_records).items())
            ),
            "transformed_exact_gap_percent": _describe(exact_gaps),
        },
        "all_outcome_ledger": [
            *(item.payload() for item in source_records),
            *(item.payload() for item in exact_records),
        ],
        "statistical_disposition": "S-PASS",
        "claim_disposition": "C-NO-CLAIM",
        "supported_wording": (
            "Deterministic descriptive gap and outcome summaries were reproduced for all "
            "42 frozen records with source-BKS and derived-exact domains kept separate."
        ),
        "prohibited_wording": [
            "RouteMind is optimal or superior on Solomon or Gehring-Homberger.",
            "Vehicle, distance, source-model, and transformed-model gaps form one scalar.",
            "The fixed descriptive census establishes population behavior.",
        ],
    }


def run_gap_analysis(
    protocol_path: Path,
    repository_root: Path,
    data_root: Path,
    output_directory: Path,
    campaign_id: str,
    code_revision: str,
    implementation_ci_run: int,
) -> Path:
    protocol = load_gap_analysis_protocol(protocol_path)
    output = _validated_output_directory(protocol, data_root, output_directory)
    if not output.is_dir():
        raise BenchmarkGapAnalysisError("campaign output directory must already exist")
    result = analyze_frozen_results(
        protocol,
        repository_root,
        data_root,
        campaign_id,
        code_revision,
        implementation_ci_run,
    )
    return _write_json_once(output / "gap-analysis.json", result)


def _source_records(
    contract: FrozenGapInput, summary: Mapping[str, object]
) -> tuple[SourceGapRecord, ...]:
    selection = _mapping(_required(summary, "selection"), "selection")
    if (
        _integer(selection, "selected") != contract.selected
        or _integer(selection, "retained") != contract.retained
    ):
        raise BenchmarkGapAnalysisError(f"{contract.task_id} selection counts drifted")
    runs = tuple(
        _mapping(item, f"{contract.task_id} run")
        for item in _sequence(_required(summary, "runs"), "runs")
    )
    if len(runs) != contract.retained:
        raise BenchmarkGapAnalysisError(f"{contract.task_id} run count drifted")
    identities = tuple(_string(item, "instance_id") for item in runs)
    if len(set(identities)) != len(identities):
        raise BenchmarkGapAnalysisError(f"{contract.task_id} run identities are not unique")

    records = tuple(_source_record(contract.task_id, run) for run in runs)
    actual_outcomes = Counter(item.outcome for item in records)
    outcome_container = (
        summary
        if contract.task_id == "R3-311"
        else _mapping(_required(summary, "result"), "result")
    )
    reported = _counter(_mapping(_required(outcome_container, "outcomes"), "outcomes"))
    if reported != actual_outcomes:
        raise BenchmarkGapAnalysisError(f"{contract.task_id} outcome counts drifted")
    return records


def _source_record(task_id: str, run: Mapping[str, object]) -> SourceGapRecord:
    instance_id = _string(run, "instance_id")
    outcome = _string(run, "outcome")
    if outcome not in _OUTCOMES:
        raise BenchmarkGapAnalysisError(f"{task_id}:{instance_id} has an unknown outcome")
    vehicles = _optional_integer(run, "vehicles")
    distance = _optional_number(run, "distance_2dp")
    reference_vehicles = _positive_integer(run, "reference_vehicles")
    reference_distance = _number(run, "reference_distance")
    if reference_distance <= 0:
        raise BenchmarkGapAnalysisError(f"{task_id}:{instance_id} reference distance is invalid")
    comparison_key = "reference_comparison" if task_id == "R3-311" else "comparison"
    comparison = _string(run, comparison_key)
    if comparison not in _REFERENCE_STATUSES:
        raise BenchmarkGapAnalysisError(f"{task_id}:{instance_id} reference status is unknown")
    accepted = (
        _boolean(run, "accepted_verified_complete") if task_id == "R3-311" else vehicles is not None
    )
    if accepted != (outcome in _INCUMBENT_OUTCOMES):
        raise BenchmarkGapAnalysisError(f"{task_id}:{instance_id} incumbent/outcome mismatch")
    if accepted and (vehicles is None or vehicles <= 0 or distance is None or distance < 0):
        raise BenchmarkGapAnalysisError(f"{task_id}:{instance_id} incumbent fields are invalid")
    if not accepted and (vehicles is not None or distance is not None):
        raise BenchmarkGapAnalysisError(f"{task_id}:{instance_id} no-incumbent fields must be null")

    reported_distance_gap = _optional_number(run, "distance_gap_percent")
    vehicle_gap: float | None = None
    distance_gap: float | None = None
    vehicle_omission: str | None = None
    distance_omission: str | None = None
    if comparison in _VEHICLE_GAP_ALLOWED:
        if not accepted or vehicles is None:
            raise BenchmarkGapAnalysisError(
                f"{task_id}:{instance_id} comparison needs an incumbent"
            )
        vehicle_gap = 100.0 * (vehicles - reference_vehicles) / reference_vehicles
        if comparison == "COMPARABLE_SAME_VEHICLE_COUNT" and vehicles != reference_vehicles:
            raise BenchmarkGapAnalysisError(
                f"{task_id}:{instance_id} equal-vehicle status is false"
            )
        if comparison == "VEHICLE_COUNT_WORSE" and vehicles <= reference_vehicles:
            raise BenchmarkGapAnalysisError(
                f"{task_id}:{instance_id} worse-vehicle direction is false"
            )
        if comparison == "VEHICLE_COUNT_BETTER" and vehicles >= reference_vehicles:
            raise BenchmarkGapAnalysisError(
                f"{task_id}:{instance_id} better-vehicle direction is false"
            )
    else:
        vehicle_omission = comparison

    if comparison == "COMPARABLE_SAME_VEHICLE_COUNT":
        assert distance is not None
        distance_gap = 100.0 * (distance - reference_distance) / reference_distance
        if reported_distance_gap is None or not isclose(
            reported_distance_gap, distance_gap, rel_tol=0, abs_tol=1e-9
        ):
            raise BenchmarkGapAnalysisError(f"{task_id}:{instance_id} distance gap mismatch")
    else:
        if reported_distance_gap is not None:
            raise BenchmarkGapAnalysisError(f"{task_id}:{instance_id} forbidden distance gap")
        distance_omission = (
            "VEHICLE_COUNT_MISMATCH" if comparison in _VEHICLE_GAP_ALLOWED else comparison
        )
    if comparison == "REFERENCE_GAP_NOT_APPLICABLE" and accepted:
        raise BenchmarkGapAnalysisError(f"{task_id}:{instance_id} N/A comparison has an incumbent")
    if comparison == "REFERENCE_QUALITY_REVIEW" and not accepted:
        raise BenchmarkGapAnalysisError(
            f"{task_id}:{instance_id} quality review lacks an incumbent"
        )
    return SourceGapRecord(
        task_id,
        instance_id,
        outcome,
        accepted,
        comparison,
        vehicles,
        reference_vehicles,
        vehicle_gap,
        distance_gap,
        vehicle_omission,
        distance_omission,
    )


def _exact_records(
    contract: FrozenGapInput, summary: Mapping[str, object], data_root: Path
) -> tuple[ExactGapRecord, ...]:
    selection = _mapping(_required(summary, "selection"), "selection")
    if (
        _integer(selection, "selected") != contract.selected
        or _integer(selection, "retained") != contract.retained
    ):
        raise BenchmarkGapAnalysisError("R3-315 selection counts drifted")
    result = _mapping(_required(summary, "result"), "result")
    for key in (
        "enumeration_complete",
        "cp_sat_optimal",
        "objective_equals_best_bound",
        "independently_verified",
        "transformed_model_ground_truth",
        "candidate_same_vehicle_count",
        "candidate_zero_transformed_distance_gap",
    ):
        if _integer(result, key) != contract.retained:
            raise BenchmarkGapAnalysisError(f"R3-315 aggregate {key} drifted")
    runs = tuple(
        _mapping(item, "R3-315 run") for item in _sequence(_required(summary, "runs"), "runs")
    )
    if len(runs) != contract.retained:
        raise BenchmarkGapAnalysisError("R3-315 run count drifted")
    identities = tuple(_string(item, "derived_instance_id") for item in runs)
    if len(set(identities)) != len(identities):
        raise BenchmarkGapAnalysisError("R3-315 derived identities are not unique")
    external_root = _resolve_below(
        data_root,
        _safe_relative_path(summary, "external_result_relative_root"),
        "R3-315 external result root",
    )
    campaign_id = _string(summary, "campaign_id")
    code_revision = _string(summary, "code_revision")
    return tuple(_exact_record(run, external_root, campaign_id, code_revision) for run in runs)


def _exact_record(
    run: Mapping[str, object], external_root: Path, campaign_id: str, code_revision: str
) -> ExactGapRecord:
    source_id = _string(run, "instance_id")
    derived_id = _string(run, "derived_instance_id")
    if _string(run, "exact_status") != "OPTIMAL":
        raise BenchmarkGapAnalysisError(f"R3-315:{derived_id} lacks exact optimal status")
    artifact = _mapping(_required(run, "artifact"), "artifact")
    artifact_name = _safe_relative_path(artifact, "name")
    artifact_sha = _digest(artifact, "sha256")
    artifact_path = _resolve_below(external_root, artifact_name, "R3-315 exact artifact")
    try:
        raw = artifact_path.read_bytes()
        sidecar = (
            artifact_path.with_suffix(artifact_path.suffix + ".sha256")
            .read_text(encoding="ascii")
            .strip()
        )
        payload = _mapping(json.loads(raw), "R3-315 exact artifact")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BenchmarkGapAnalysisError(
            f"R3-315:{derived_id} exact artifact is unreadable"
        ) from exc
    actual_sha = sha256(raw).hexdigest()
    if sidecar != artifact_sha or actual_sha != artifact_sha:
        raise BenchmarkGapAnalysisError(f"R3-315:{derived_id} exact artifact checksum mismatch")
    if _integer(artifact, "bytes") != len(raw):
        raise BenchmarkGapAnalysisError(f"R3-315:{derived_id} exact artifact byte count mismatch")
    if (
        _string(payload, "campaign_id") != campaign_id
        or _string(payload, "code_revision") != code_revision
    ):
        raise BenchmarkGapAnalysisError(f"R3-315:{derived_id} exact artifact lineage mismatch")

    comparison = _mapping(_required(payload, "comparison"), "comparison")
    exact = _mapping(_required(payload, "exact_reference"), "exact_reference")
    candidate = _mapping(_required(payload, "candidate"), "candidate")
    if _string(comparison, "status") != "COMPARABLE_SAME_VEHICLE_COUNT":
        raise BenchmarkGapAnalysisError(f"R3-315:{derived_id} comparison is not hierarchical")
    if _integer(comparison, "vehicle_count_gap") != 0:
        raise BenchmarkGapAnalysisError(f"R3-315:{derived_id} vehicle counts differ")
    candidate_distance = _positive_integer(comparison, "candidate_transformed_distance")
    exact_distance = _positive_integer(comparison, "exact_transformed_distance")
    recomputed_gap = 100.0 * (candidate_distance - exact_distance) / exact_distance
    artifact_gap = _number(comparison, "transformed_distance_gap_percent")
    summary_gap = _number(run, "transformed_distance_gap_percent")
    if not isclose(artifact_gap, recomputed_gap, rel_tol=0, abs_tol=1e-9) or not isclose(
        summary_gap, recomputed_gap, rel_tol=0, abs_tol=1e-9
    ):
        raise BenchmarkGapAnalysisError(f"R3-315:{derived_id} transformed gap mismatch")
    if _integer(run, "transformed_distance") != candidate_distance:
        raise BenchmarkGapAnalysisError(f"R3-315:{derived_id} transformed distance drifted")
    if (
        _string(exact, "status") != "OPTIMAL"
        or _string(exact, "ground_truth_status") != "TRANSFORMED_MODEL_GROUND_TRUTH"
    ):
        raise BenchmarkGapAnalysisError(f"R3-315:{derived_id} proof scope drifted")
    if _integer(exact, "objective_value") != _integer(exact, "best_objective_bound"):
        raise BenchmarkGapAnalysisError(f"R3-315:{derived_id} exact bound differs")
    vehicles = _positive_integer(run, "vehicles")
    candidate_solution = _mapping(_required(candidate, "solution"), "candidate.solution")
    if (
        _positive_integer(candidate_solution, "claimed_vehicle_count") != vehicles
        or _positive_integer(exact, "selected_route_count") != vehicles
    ):
        raise BenchmarkGapAnalysisError(f"R3-315:{derived_id} vehicle lineage drifted")
    for label, container in (("candidate", candidate), ("exact", exact)):
        verification = _mapping(_required(container, "verification"), f"{label}.verification")
        if not _boolean(verification, "valid") or not _boolean(verification, "complete"):
            raise BenchmarkGapAnalysisError(f"R3-315:{derived_id} {label} verification failed")
    return ExactGapRecord(
        "R3-315",
        source_id,
        derived_id,
        _string(run, "exact_status"),
        _string(run, "candidate_status"),
        recomputed_gap,
        artifact_name,
        artifact_sha,
    )


def _source_summary(records: tuple[SourceGapRecord, ...]) -> dict[str, object]:
    outcomes = Counter(item.outcome for item in records)
    denominator = len(records)
    accepted = sum(item.accepted_verified_complete for item in records)
    timeout_with = outcomes["TIMEOUT_WITH_FEASIBLE"]
    timeout_without = outcomes["TIMEOUT_NO_FEASIBLE"]
    resource = outcomes["RESOURCE_LIMIT_WITH_FEASIBLE"] + outcomes["RESOURCE_LIMIT_NO_FEASIBLE"]
    return {
        "records": denominator,
        "outcomes": {outcome: outcomes[outcome] for outcome in _OUTCOMES},
        "rates": {
            "verified_complete_rate": _rate(accepted, denominator),
            "any_timeout_rate": _rate(timeout_with + timeout_without, denominator),
            "timeout_with_feasible_rate": _rate(timeout_with, denominator),
            "timeout_no_feasible_rate": _rate(timeout_without, denominator),
            "infeasible_proven_rate": _rate(outcomes["INFEASIBLE_PROVEN"], denominator),
            "resource_limit_rate": _rate(resource, denominator),
            "failed_rate": _rate(outcomes["FAILED"], denominator),
        },
        "reference_comparisons": {
            status: sum(item.comparison == status for item in records)
            for status in _REFERENCE_STATUSES
        },
        "vehicle_gap_percent": _describe(
            tuple(
                item.vehicle_gap_percent for item in records if item.vehicle_gap_percent is not None
            )
        ),
        "same_vehicle_distance_gap_percent": _describe(
            tuple(
                item.distance_gap_percent
                for item in records
                if item.distance_gap_percent is not None
            )
        ),
        "numeric_omissions": {
            "vehicle_gap": dict(
                sorted(
                    Counter(
                        item.vehicle_gap_omission
                        for item in records
                        if item.vehicle_gap_omission is not None
                    ).items()
                )
            ),
            "distance_gap": dict(
                sorted(
                    Counter(
                        item.distance_gap_omission
                        for item in records
                        if item.distance_gap_omission is not None
                    ).items()
                )
            ),
        },
    }


def _describe(values: tuple[float, ...]) -> dict[str, object]:
    if not values:
        return {"n": 0, "minimum": None, "median": None, "p90": None, "maximum": None}
    if any(not isfinite(item) for item in values):
        raise BenchmarkGapAnalysisError("gap distribution contains a non-finite value")
    ordered = tuple(sorted(values))
    return {
        "n": len(ordered),
        "minimum": ordered[0],
        "median": median(ordered),
        "p90": _type7_percentile(ordered, 0.9),
        "maximum": ordered[-1],
    }


def _type7_percentile(ordered: tuple[float, ...], quantile: float) -> float:
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _load_frozen_summary(contract: FrozenGapInput, repository_root: Path) -> Mapping[str, object]:
    path = _resolve_below(repository_root, contract.relative_path, f"{contract.task_id} input")
    try:
        raw = path.read_bytes()
        root = _mapping(json.loads(raw), f"{contract.task_id} summary")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BenchmarkGapAnalysisError(f"{contract.task_id} summary is unreadable") from exc
    if sha256(raw).hexdigest() != contract.sha256:
        raise BenchmarkGapAnalysisError(f"{contract.task_id} input checksum mismatch")
    if _string(root, "schema_version") != contract.schema_version:
        raise BenchmarkGapAnalysisError(f"{contract.task_id} input schema drifted")
    if _string(root, "task_id") != contract.task_id:
        raise BenchmarkGapAnalysisError(f"{contract.task_id} input task identity drifted")
    if _string(root, "manifest_id") != contract.manifest_id:
        raise BenchmarkGapAnalysisError(f"{contract.task_id} input manifest drifted")
    return root


def _validated_output_directory(
    protocol: GapAnalysisProtocol, data_root: Path, output_directory: Path
) -> Path:
    root = data_root.expanduser().resolve()
    allowed = _resolve_below(root, protocol.result_relative_root, "R3-316 result boundary")
    target = output_directory.expanduser().resolve()
    try:
        target.relative_to(allowed)
    except ValueError as exc:
        raise BenchmarkGapAnalysisError(
            "campaign output must remain below the frozen data root"
        ) from exc
    if target == allowed:
        raise BenchmarkGapAnalysisError("campaign output must use a distinct campaign directory")
    return target


def _write_json_once(path: Path, payload: Mapping[str, object]) -> Path:
    encoded = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    try:
        with path.open("xb") as stream:
            stream.write(encoded)
        with path.with_suffix(path.suffix + ".sha256").open("x", encoding="ascii") as stream:
            stream.write(sha256(encoded).hexdigest() + "\n")
    except FileExistsError as exc:
        raise BenchmarkGapAnalysisError("immutable gap analysis artifact already exists") from exc
    except OSError as exc:
        raise BenchmarkGapAnalysisError("unable to write gap analysis artifact") from exc
    return path


def _frozen_input(value: Mapping[str, object]) -> FrozenGapInput:
    selected = _positive_integer(value, "selected")
    return FrozenGapInput(
        task_id=_string(value, "task_id"),
        relative_path=_safe_relative_path(value, "path"),
        sha256=_digest(value, "sha256"),
        schema_version=_string(value, "schema_version"),
        manifest_id=_string(value, "manifest_id"),
        selected=selected,
        retained=_positive_integer(value, "retained"),
        analysis_domain=_string(value, "analysis_domain"),
    )


def _resolve_below(root: Path, relative: str, label: str) -> Path:
    base = root.expanduser().resolve()
    parts = PurePosixPath(relative).parts
    target = base.joinpath(*parts).resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise BenchmarkGapAnalysisError(f"{label} escapes its root") from exc
    return target


def _safe_relative_path(value: Mapping[str, object], key: str) -> str:
    item = _string(value, key)
    path = PurePosixPath(item)
    if path.is_absolute() or "\\" in item or any(part in {"", ".."} for part in path.parts):
        raise BenchmarkGapAnalysisError(f"{key} must be a safe relative POSIX path")
    return item


def _counter(value: Mapping[str, object]) -> Counter[str]:
    result: Counter[str] = Counter()
    for key, item in value.items():
        if key not in _OUTCOMES:
            raise BenchmarkGapAnalysisError(f"unknown reported outcome: {key}")
        if not isinstance(item, int) or isinstance(item, bool) or item <= 0:
            raise BenchmarkGapAnalysisError("reported outcome counts must be positive integers")
        result[key] = item
    return result


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise BenchmarkGapAnalysisError(f"{label} must be an object")
    return cast(Mapping[str, object], value)


def _sequence(value: object, label: str) -> Sequence[object]:
    if not isinstance(value, list):
        raise BenchmarkGapAnalysisError(f"{label} must be an array")
    return cast(Sequence[object], value)


def _required(value: Mapping[str, object], key: str) -> object:
    if key not in value:
        raise BenchmarkGapAnalysisError(f"{key} is required")
    return value[key]


def _string(value: Mapping[str, object], key: str) -> str:
    item = _required(value, key)
    if not isinstance(item, str) or not item.strip():
        raise BenchmarkGapAnalysisError(f"{key} must be a non-blank string")
    return item


def _string_array(value: Mapping[str, object], key: str) -> tuple[str, ...]:
    items = _sequence(_required(value, key), key)
    if any(not isinstance(item, str) or not item.strip() for item in items):
        raise BenchmarkGapAnalysisError(f"{key} must contain non-blank strings")
    return cast(tuple[str, ...], tuple(items))


def _boolean(value: Mapping[str, object], key: str) -> bool:
    item = _required(value, key)
    if not isinstance(item, bool):
        raise BenchmarkGapAnalysisError(f"{key} must be boolean")
    return item


def _integer(value: Mapping[str, object], key: str) -> int:
    item = _required(value, key)
    if not isinstance(item, int) or isinstance(item, bool):
        raise BenchmarkGapAnalysisError(f"{key} must be an integer")
    return item


def _positive_integer(value: Mapping[str, object], key: str) -> int:
    item = _integer(value, key)
    if item <= 0:
        raise BenchmarkGapAnalysisError(f"{key} must be positive")
    return item


def _optional_integer(value: Mapping[str, object], key: str) -> int | None:
    item = value.get(key)
    if item is None:
        return None
    if not isinstance(item, int) or isinstance(item, bool):
        raise BenchmarkGapAnalysisError(f"{key} must be an integer or null")
    return item


def _number(value: Mapping[str, object], key: str) -> float:
    item = _required(value, key)
    if not isinstance(item, (int, float)) or isinstance(item, bool) or not isfinite(item):
        raise BenchmarkGapAnalysisError(f"{key} must be finite numeric")
    return float(item)


def _optional_number(value: Mapping[str, object], key: str) -> float | None:
    item = value.get(key)
    if item is None:
        return None
    if not isinstance(item, (int, float)) or isinstance(item, bool) or not isfinite(item):
        raise BenchmarkGapAnalysisError(f"{key} must be finite numeric or null")
    return float(item)


def _digest(value: Mapping[str, object], key: str) -> str:
    item = _string(value, key)
    if not _SHA256.fullmatch(item):
        raise BenchmarkGapAnalysisError(f"{key} must be a lowercase SHA-256 digest")
    return item


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run frozen R3-316 benchmark gap analysis")
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--code-revision", required=True)
    parser.add_argument("--implementation-ci-run", type=int, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        path = run_gap_analysis(
            arguments.protocol,
            arguments.repository_root,
            arguments.data_root,
            arguments.output_directory,
            arguments.campaign_id,
            arguments.code_revision,
            arguments.implementation_ci_run,
        )
    except (BenchmarkGapAnalysisError, OSError, ValueError) as exc:
        print(f"R3-316 gap analysis failed: {exc}", file=sys.stderr)
        return 2
    print(path)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
