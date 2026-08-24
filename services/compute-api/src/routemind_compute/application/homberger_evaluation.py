from __future__ import annotations

import argparse
import json
import platform
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from importlib.metadata import version
from math import isfinite
from pathlib import Path, PurePosixPath
from time import perf_counter
from typing import cast
from zipfile import BadZipFile, ZipFile

from routemind_compute.application.artifacts import (
    DataArtifactManifest,
    DataRootArtifactAdapter,
)
from routemind_compute.application.public_benchmarks import (
    BenchmarkReferenceValue,
    LicenseStatus,
    ParsedPublicBenchmark,
    PublicBenchmarkSourceManifest,
    PublicVrptwSolution,
    ReferenceStatus,
    load_public_benchmark,
)
from routemind_compute.application.solomon_evaluation import solve_canonical_vrptw
from routemind_compute.application.solver_outcomes import (
    ClassifiedSolverRun,
    SolverProof,
    SolverResourceLimits,
    SolverResourceUsage,
    SolverRunObservation,
    SolverTermination,
    classify_solver_run,
)
from routemind_compute.application.verification import PublicVrptwVerificationReport

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REVISION = re.compile(r"^[0-9a-f]{40}$")
_SUPPORTED_SCHEMA = "routemind-gehring-homberger-experiment-v1"
_CUSTOMER_COUNTS = (200, 400, 600, 800, 1000)
_FAMILIES = ("C1", "C2", "R1", "R2", "RC1", "RC2")
_STATUS_ERROR = {"ROUTING_INVALID", "ROUTING_NOT_SOLVED"}
_ORTOOLS_VERSION = version("ortools")


class HombergerEvaluationError(ValueError):
    """Raised when the frozen Homberger protocol or an output is invalid."""


@dataclass(frozen=True, slots=True)
class HombergerArchive:
    customer_count: int
    source_page_url: str
    download_url: str
    relative_path: str
    bytes: int
    sha256: str
    member_count: int


@dataclass(frozen=True, slots=True)
class HombergerSource:
    family: str
    catalog_url: str
    documentation_url: str
    license_status: str
    parser_id: str
    parser_version: str
    archives: tuple[HombergerArchive, ...]

    def archive(self, customer_count: int) -> HombergerArchive:
        matches = [item for item in self.archives if item.customer_count == customer_count]
        if len(matches) != 1:
            raise HombergerEvaluationError(
                f"customer count {customer_count} has no unique source archive"
            )
        return matches[0]


@dataclass(frozen=True, slots=True)
class HombergerSelection:
    customer_count: int
    family: str
    instance_id: str
    archive_member: str
    relative_path: str
    sha256: str
    reference_vehicle_count: int
    reference_distance: float
    reference_status: str
    reference_comparison_allowed: bool
    reference_note: str | None


@dataclass(frozen=True, slots=True)
class HombergerProtocol:
    manifest_id: str
    frozen_at_utc: str
    frozen_against_revision: str
    manifest_sha256: str
    source: HombergerSource
    instances: tuple[HombergerSelection, ...]
    solver_version: str
    seed: int
    wall_time_seconds: float
    threads: int
    integer_scale: int
    result_relative_root: str

    def selection(self, instance_id: str) -> HombergerSelection:
        matches = [item for item in self.instances if item.instance_id == instance_id]
        if len(matches) != 1:
            raise HombergerEvaluationError(f"instance {instance_id} is not uniquely selected")
        return matches[0]


@dataclass(frozen=True, slots=True)
class HombergerReferenceComparison:
    status: str
    comparison_allowed: bool
    reference_vehicle_count: int
    reference_distance: float
    reference_note: str | None
    result_vehicle_count: int | None
    result_distance_2dp: float | None
    distance_gap_percent: float | None

    def payload(self) -> dict[str, object]:
        return {
            "status": self.status,
            "comparison_allowed": self.comparison_allowed,
            "reference_vehicle_count": self.reference_vehicle_count,
            "reference_distance": self.reference_distance,
            "reference_note": self.reference_note,
            "result_vehicle_count": self.result_vehicle_count,
            "result_distance_2dp": self.result_distance_2dp,
            "distance_gap_percent": self.distance_gap_percent,
        }


@dataclass(frozen=True, slots=True)
class HombergerSolverRun:
    run_id: str
    campaign_id: str
    code_revision: str
    started_at_utc: str
    completed_at_utc: str
    manifest_id: str
    manifest_sha256: str
    selection: HombergerSelection
    parsed: ParsedPublicBenchmark
    ortools_status_code: int
    ortools_status: str
    elapsed_seconds: float
    fixed_vehicle_cost: int
    solution: PublicVrptwSolution | None
    verification: PublicVrptwVerificationReport | None
    classified: ClassifiedSolverRun
    comparison: HombergerReferenceComparison

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "routemind-homberger-run-v1",
            "run_id": self.run_id,
            "campaign_id": self.campaign_id,
            "code_revision": self.code_revision,
            "manifest_id": self.manifest_id,
            "manifest_sha256": self.manifest_sha256,
            "started_at_utc": self.started_at_utc,
            "completed_at_utc": self.completed_at_utc,
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "ortools": _ORTOOLS_VERSION,
            },
            "instance": {
                "customer_count": self.selection.customer_count,
                "family": self.selection.family,
                "instance_id": self.selection.instance_id,
                "archive_member": self.selection.archive_member,
                "artifact_sha256": self.parsed.artifact_sha256,
                "canonical_digest": self.parsed.instance.digest,
                "lineage_digest": self.parsed.lineage_digest,
            },
            "solver": {
                "name": "Google OR-Tools RoutingModel",
                "version": _ORTOOLS_VERSION,
                "status_code": self.ortools_status_code,
                "status": self.ortools_status,
                "routing_random_seed": "SEED_API_NOT_AVAILABLE",
                "sat_random_seed": 0,
                "threads": 1,
                "elapsed_seconds": self.elapsed_seconds,
                "fixed_vehicle_cost": self.fixed_vehicle_cost,
            },
            "classification": self.classified.payload(),
            "solution": _solution_payload(self.solution),
            "verification": _verification_payload(self.verification),
            "reference_comparison": self.comparison.payload(),
        }


def load_homberger_protocol(path: Path) -> HombergerProtocol:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HombergerEvaluationError("Homberger protocol is unreadable") from exc
    root = _mapping(value, "protocol")
    if _string(root, "schema_version") != _SUPPORTED_SCHEMA:
        raise HombergerEvaluationError("Homberger protocol schema is unsupported")
    if _boolean(root, "material_execution_started"):
        raise HombergerEvaluationError("frozen protocol must precede material execution")
    revision = _string(root, "frozen_against_revision")
    if not _REVISION.fullmatch(revision):
        raise HombergerEvaluationError("frozen revision must be a full lowercase Git SHA")

    source_value = _mapping(_required(root, "source"), "source")
    archives = tuple(
        _archive(_mapping(item, "source archive"))
        for item in _sequence(_required(source_value, "archives"), "archives")
    )
    if tuple(item.customer_count for item in archives) != _CUSTOMER_COUNTS:
        raise HombergerEvaluationError("source archives must cover the five frozen scales in order")

    selection_value = _mapping(_required(root, "selection"), "selection")
    if tuple(_integer_array(selection_value, "customer_counts")) != _CUSTOMER_COUNTS:
        raise HombergerEvaluationError("selection customer counts differ from frozen scales")
    if tuple(_string_array(selection_value, "structural_families")) != _FAMILIES:
        raise HombergerEvaluationError("selection families differ from the frozen six families")
    instances = tuple(
        _selection(_mapping(item, "selected instance"))
        for item in _sequence(_required(selection_value, "instances"), "instances")
    )
    if _integer(selection_value, "selected_count") != len(instances) or len(instances) != 30:
        raise HombergerEvaluationError("selected_count must match exactly 30 instances")
    expected = tuple((count, family) for count in _CUSTOMER_COUNTS for family in _FAMILIES)
    if tuple((item.customer_count, item.family) for item in instances) != expected:
        raise HombergerEvaluationError(
            "instances must preserve the frozen scale-family census order"
        )
    if len({item.instance_id for item in instances}) != len(instances):
        raise HombergerEvaluationError("selected instance identities must be unique")
    for selected in instances:
        expected_id = f"{selected.family}_{selected.customer_count // 100}_1"
        if selected.instance_id != expected_id or selected.archive_member != f"{expected_id}.TXT":
            raise HombergerEvaluationError("selected instance violates the first-replicate rule")

    solver_value = _mapping(_required(root, "solver"), "solver")
    resource_value = _mapping(_required(root, "resource_policy"), "resource_policy")
    modeling_value = _mapping(_required(root, "modeling"), "modeling")
    verification_value = _mapping(_required(root, "verification"), "verification")
    analysis_value = _mapping(_required(root, "analysis_plan"), "analysis_plan")
    artifact_value = _mapping(_required(root, "artifact_policy"), "artifact_policy")
    if _string(solver_value, "package") != "ortools":
        raise HombergerEvaluationError("R3-312 solver package must be ortools")
    threads = _integer(solver_value, "threads")
    if threads != 1:
        raise HombergerEvaluationError("R3-312 requires one solver thread")
    wall_time = _number(resource_value, "wall_time_seconds_per_instance")
    if wall_time <= 0:
        raise HombergerEvaluationError("solver wall time must be positive")
    if _integer(resource_value, "maximum_instances") != len(instances):
        raise HombergerEvaluationError("maximum_instances must match the frozen census")
    maximum_campaign_time = _number(resource_value, "maximum_campaign_solver_wall_time_seconds")
    if maximum_campaign_time != wall_time * len(instances):
        raise HombergerEvaluationError(
            "campaign solver bound must equal per-instance bound times 30"
        )
    if _string(resource_value, "process_isolation") != "ONE_INSTANCE_PER_PROCESS_SEQUENTIAL":
        raise HombergerEvaluationError(
            "R3-312 requires one sequential isolated process per instance"
        )
    integer_scale = _positive_integer(modeling_value, "integer_scale")
    if _string(verification_value, "verifier_revision") != "R3-314":
        raise HombergerEvaluationError("R3-312 requires the frozen R3-314 verifier")
    if _string(verification_value, "outcome_contract_revision") != "R3-317":
        raise HombergerEvaluationError("R3-312 requires the frozen R3-317 outcome contract")
    if _string(analysis_value, "statistical_disposition") != "S-NOT-APPLICABLE":
        raise HombergerEvaluationError("R3-312 fixed census must remain S-NOT-APPLICABLE")
    result_relative_root = _safe_relative_path(artifact_value, "result_relative_root")

    source = HombergerSource(
        family=_string(source_value, "family"),
        catalog_url=_string(source_value, "catalog_url"),
        documentation_url=_string(source_value, "documentation_url"),
        license_status=_string(source_value, "license_status"),
        parser_id=_string(source_value, "parser_id"),
        parser_version=_string(source_value, "parser_version"),
        archives=archives,
    )
    protocol = HombergerProtocol(
        manifest_id=_string(root, "manifest_id"),
        frozen_at_utc=_string(root, "frozen_at_utc"),
        frozen_against_revision=revision,
        manifest_sha256=sha256(raw).hexdigest(),
        source=source,
        instances=instances,
        solver_version=_string(solver_value, "version"),
        seed=_integer(solver_value, "sat_random_seed"),
        wall_time_seconds=wall_time,
        threads=threads,
        integer_scale=integer_scale,
        result_relative_root=result_relative_root,
    )
    if protocol.solver_version != _ORTOOLS_VERSION:
        raise HombergerEvaluationError("installed OR-Tools version differs from frozen protocol")
    return protocol


def source_manifest(
    protocol: HombergerProtocol, selected: HombergerSelection
) -> PublicBenchmarkSourceManifest:
    archive = protocol.source.archive(selected.customer_count)
    artifact = DataArtifactManifest(
        artifact_id=f"homberger-{selected.instance_id.lower()}",
        artifact_type="benchmark",
        relative_path=selected.relative_path,
        sha256=selected.sha256,
        producer="SINTEF Gehring-Homberger benchmark archive",
        revision=f"sha256:{archive.sha256}",
        configuration=(
            ("archive_member", selected.archive_member),
            ("customer_count", str(selected.customer_count)),
            ("distance_semantics", "EUCLIDEAN_DOUBLE"),
            ("objective_semantics", "HIERARCHICAL_VEHICLES_THEN_DISTANCE"),
        ),
        seed=protocol.seed,
    )
    note = "SINTEF hierarchical vehicle-count then double-distance best-known reference."
    if selected.reference_note is not None:
        note = f"{note} {selected.reference_note}"
    reference = BenchmarkReferenceValue(
        reference_id=f"sintef-{selected.instance_id.lower()}-hierarchical-double-2026-08-24",
        instance_id=selected.instance_id,
        reference_status=cast(ReferenceStatus, selected.reference_status),
        vehicle_count=selected.reference_vehicle_count,
        distance=selected.reference_distance,
        objective_semantics="HIERARCHICAL_VEHICLES_THEN_DISTANCE",
        numeric_semantics="EUCLIDEAN_DOUBLE_DISTANCE_ROUNDED_2DP",
        source_url=archive.source_page_url,
        notes=note,
    )
    return PublicBenchmarkSourceManifest(
        source_id=f"{protocol.manifest_id}-{selected.instance_id.lower()}",
        family=protocol.source.family,
        instance_id=selected.instance_id,
        source_page_url=archive.source_page_url,
        download_url=archive.download_url,
        retrieved_at_utc=protocol.frozen_at_utc,
        license_status=cast(LicenseStatus, protocol.source.license_status),
        terms_url=protocol.source.documentation_url,
        redistribution_allowed=False,
        distribution_sha256=archive.sha256,
        archive_member=selected.archive_member,
        parser_id=protocol.source.parser_id,
        parser_version=protocol.source.parser_version,
        artifact=artifact,
        references=(reference,),
    )


def verify_selected_archive(
    protocol: HombergerProtocol,
    selected: HombergerSelection,
    adapter: DataRootArtifactAdapter,
) -> None:
    archive = protocol.source.archive(selected.customer_count)
    artifact = DataArtifactManifest(
        artifact_id=f"homberger-{selected.customer_count}-archive",
        artifact_type="dataset",
        relative_path=archive.relative_path,
        sha256=archive.sha256,
        producer="SINTEF Gehring-Homberger benchmark archive",
        revision=f"sha256:{archive.sha256}",
        configuration=(("member_count", str(archive.member_count)),),
        seed=protocol.seed,
    )
    resolved = adapter.resolve(artifact)
    if resolved.path.stat().st_size != archive.bytes:
        raise HombergerEvaluationError("source archive byte count differs from frozen protocol")
    try:
        with ZipFile(resolved.path) as bundle:
            members = [item for item in bundle.infolist() if not item.is_dir()]
            if len(members) != archive.member_count:
                raise HombergerEvaluationError(
                    "source archive member count differs from frozen protocol"
                )
            matches = [item for item in members if item.filename == selected.archive_member]
            if len(matches) != 1:
                raise HombergerEvaluationError("selected archive member is not unique")
            with bundle.open(matches[0]) as stream:
                digest = sha256()
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != selected.sha256:
                raise HombergerEvaluationError("selected archive member checksum mismatch")
    except (BadZipFile, OSError) as exc:
        raise HombergerEvaluationError("source archive cannot be verified") from exc


def compare_reference(
    selected: HombergerSelection,
    verification: PublicVrptwVerificationReport | None,
) -> HombergerReferenceComparison:
    if verification is None or not verification.valid or not verification.complete:
        vehicles = None
        distance = None
    else:
        vehicles = verification.recomputed_vehicle_count
        distance = round(verification.recomputed_total_distance, 2)
    if not selected.reference_comparison_allowed:
        return HombergerReferenceComparison(
            "REFERENCE_QUALITY_REVIEW",
            False,
            selected.reference_vehicle_count,
            selected.reference_distance,
            selected.reference_note,
            vehicles,
            distance,
            None,
        )
    if vehicles is None or distance is None:
        return HombergerReferenceComparison(
            "REFERENCE_GAP_NOT_APPLICABLE",
            True,
            selected.reference_vehicle_count,
            selected.reference_distance,
            selected.reference_note,
            vehicles,
            distance,
            None,
        )
    assert vehicles is not None and distance is not None
    if vehicles > selected.reference_vehicle_count:
        status = "VEHICLE_COUNT_WORSE"
        gap = None
    elif vehicles < selected.reference_vehicle_count:
        status = "REFERENCE_CONTRADICTION_REVIEW"
        gap = None
    else:
        status = "COMPARABLE_SAME_VEHICLE_COUNT"
        gap = (distance - selected.reference_distance) / selected.reference_distance * 100
    return HombergerReferenceComparison(
        status,
        True,
        selected.reference_vehicle_count,
        selected.reference_distance,
        selected.reference_note,
        vehicles,
        distance,
        gap,
    )


def solve_homberger_instance(
    protocol: HombergerProtocol,
    selected: HombergerSelection,
    parsed: ParsedPublicBenchmark,
    *,
    campaign_id: str,
    code_revision: str,
) -> HombergerSolverRun:
    if not _REVISION.fullmatch(code_revision):
        raise HombergerEvaluationError("code revision must be a full lowercase Git SHA")
    if parsed.instance.instance_id.casefold() != selected.instance_id.casefold():
        raise HombergerEvaluationError("parsed instance does not match selected instance")
    started_at = _utc_now()
    outer_started = perf_counter()
    try:
        canonical = solve_canonical_vrptw(
            parsed.instance,
            integer_scale=protocol.integer_scale,
            wall_time_seconds=protocol.wall_time_seconds,
            threads=protocol.threads,
            seed=protocol.seed,
        )
        elapsed = canonical.elapsed_seconds
        status_code = canonical.status_code
        status = canonical.status
        fixed_vehicle_cost = canonical.fixed_vehicle_cost
        solution = canonical.solution
        verification = canonical.verification
        termination, proof, failure_code = _routing_termination(status)
    except MemoryError:
        elapsed = perf_counter() - outer_started
        status_code = -1
        status = "PROCESS_MEMORY_LIMIT"
        fixed_vehicle_cost = 0
        solution = None
        verification = None
        termination = SolverTermination.MEMORY_LIMIT
        proof = SolverProof.NONE
        failure_code = "PYTHON_MEMORY_ERROR"
    limits = SolverResourceLimits(
        wall_time_seconds=protocol.wall_time_seconds,
        threads=protocol.threads,
    )
    observation = SolverRunObservation(
        run_id=f"{campaign_id}:{selected.instance_id.lower()}",
        solver_name="Google OR-Tools RoutingModel",
        solver_version=_ORTOOLS_VERSION,
        termination=termination,
        proof=proof,
        usage=SolverResourceUsage(elapsed_seconds=elapsed),
        incumbent_present=solution is not None,
        verification_report=verification,
        failure_code=failure_code,
    )
    classified = classify_solver_run(observation, limits)
    return HombergerSolverRun(
        run_id=observation.run_id,
        campaign_id=campaign_id,
        code_revision=code_revision,
        started_at_utc=started_at,
        completed_at_utc=_utc_now(),
        manifest_id=protocol.manifest_id,
        manifest_sha256=protocol.manifest_sha256,
        selection=selected,
        parsed=parsed,
        ortools_status_code=status_code,
        ortools_status=status,
        elapsed_seconds=elapsed,
        fixed_vehicle_cost=fixed_vehicle_cost,
        solution=solution,
        verification=verification,
        classified=classified,
        comparison=compare_reference(selected, verification),
    )


def run_selected_instance(
    protocol_path: Path,
    data_root: Path,
    output_directory: Path,
    instance_id: str,
    campaign_id: str,
    code_revision: str,
) -> Path:
    protocol = load_homberger_protocol(protocol_path)
    selected = protocol.selection(instance_id)
    adapter = DataRootArtifactAdapter(data_root)
    verify_selected_archive(protocol, selected, adapter)
    parsed = load_public_benchmark(source_manifest(protocol, selected), adapter)
    run = solve_homberger_instance(
        protocol,
        selected,
        parsed,
        campaign_id=campaign_id,
        code_revision=code_revision,
    )
    output = _validated_output_directory(protocol, data_root, output_directory)
    output.mkdir(parents=True, exist_ok=True)
    return _write_json_once(output / f"{selected.instance_id.lower()}.json", run.payload())


def summarize_campaign(
    protocol_path: Path,
    data_root: Path,
    output_directory: Path,
    campaign_id: str,
    code_revision: str,
) -> Path:
    protocol = load_homberger_protocol(protocol_path)
    if not _REVISION.fullmatch(code_revision):
        raise HombergerEvaluationError("code revision must be a full lowercase Git SHA")
    output = _validated_output_directory(protocol, data_root, output_directory)
    results: list[Mapping[str, object]] = []
    for selected in protocol.instances:
        path = output / f"{selected.instance_id.lower()}.json"
        result = _read_verified_artifact(path)
        if _string(result, "schema_version") != "routemind-homberger-run-v1":
            raise HombergerEvaluationError("run artifact schema mismatch")
        if _string(result, "campaign_id") != campaign_id:
            raise HombergerEvaluationError("run artifact campaign identity mismatch")
        if _string(result, "code_revision") != code_revision:
            raise HombergerEvaluationError("run artifact code revision mismatch")
        if (
            _string(result, "manifest_id") != protocol.manifest_id
            or _string(result, "manifest_sha256") != protocol.manifest_sha256
        ):
            raise HombergerEvaluationError("run artifact manifest identity mismatch")
        instance = _mapping(_required(result, "instance"), "instance")
        if (
            _string(instance, "instance_id") != selected.instance_id
            or _integer(instance, "customer_count") != selected.customer_count
            or _string(instance, "family") != selected.family
            or _string(instance, "archive_member") != selected.archive_member
            or _digest(instance, "artifact_sha256") != selected.sha256
        ):
            raise HombergerEvaluationError("run artifact selected identity mismatch")
        _validate_reference_comparison(result, selected)
        results.append(result)

    scales = [
        _scale_summary(count, [item for item in results if _result_scale(item) == count])
        for count in _CUSTOMER_COUNTS
    ]
    outcomes = _outcome_counts(results)
    verified = sum(_accepted(item) for item in results)
    payload: dict[str, object] = {
        "schema_version": "routemind-homberger-campaign-summary-v1",
        "manifest_id": protocol.manifest_id,
        "manifest_sha256": protocol.manifest_sha256,
        "campaign_id": campaign_id,
        "code_revision": code_revision,
        "completed_at_utc": _utc_now(),
        "selected_count": len(results),
        "retained_count": len(results),
        "verified_complete_count": verified,
        "verified_complete_rate": verified / len(results),
        "outcomes": outcomes,
        "scales": scales,
        "statistical_disposition": "S-NOT-APPLICABLE",
        "claim_disposition": "C-NO-CLAIM",
        "limitations": [
            "Fixed first-replicate census; no random-population scale trend is authorized.",
            "Five solver seconds per instance measures bounded behavior, not solver capability.",
            "The conservative integer transform is not numerically identical to source "
            "double distance.",
            "Questioned or marked SINTEF references never receive scalar distance gaps.",
            "No optimality claim is authorized.",
        ],
        "artifacts": [f"{item.instance_id.lower()}.json" for item in protocol.instances],
    }
    return _write_json_once(output / "campaign-summary.json", payload)


def _scale_summary(
    customer_count: int, results: Sequence[Mapping[str, object]]
) -> dict[str, object]:
    if len(results) != len(_FAMILIES):
        raise HombergerEvaluationError("scale summary must retain all six structural families")
    verified = sum(_accepted(item) for item in results)
    if verified == 6:
        label = "SUPPORTED_UNDER_FROZEN_POLICY"
    elif verified == 0:
        label = "NO_VERIFIED_INCUMBENT_UNDER_FROZEN_POLICY"
    else:
        label = "DEGRADED_UNDER_FROZEN_POLICY"
    elapsed = [
        _number(_mapping(_required(item, "solver"), "solver"), "elapsed_seconds")
        for item in results
    ]
    comparisons = [
        _mapping(_required(item, "reference_comparison"), "reference_comparison")
        for item in results
    ]
    gaps = [
        {
            "instance_id": _string(
                _mapping(_required(item, "instance"), "instance"), "instance_id"
            ),
            "distance_gap_percent": _number(comparison, "distance_gap_percent"),
        }
        for item, comparison in zip(results, comparisons, strict=True)
        if comparison.get("distance_gap_percent") is not None
    ]
    comparison_statuses: dict[str, int] = {}
    for comparison in comparisons:
        status = _string(comparison, "status")
        comparison_statuses[status] = comparison_statuses.get(status, 0) + 1
    issue_count = sum(
        len(
            _sequence(
                _required(
                    _mapping(_required(item, "classification"), "classification"),
                    "verification_issue_codes",
                ),
                "verification_issue_codes",
            )
        )
        for item in results
    )
    return {
        "customer_count": customer_count,
        "selected_count": len(results),
        "retained_count": len(results),
        "verified_complete_count": verified,
        "verified_complete_rate": verified / len(results),
        "support_label": label,
        "outcomes": _outcome_counts(results),
        "elapsed_seconds": {
            "minimum": min(elapsed),
            "maximum": max(elapsed),
            "mean": sum(elapsed) / len(elapsed),
            "total": sum(elapsed),
        },
        "reference_comparison_statuses": dict(sorted(comparison_statuses.items())),
        "allowed_same_vehicle_distance_gaps": gaps,
        "verification_issue_count": issue_count,
    }


def _outcome_counts(results: Sequence[Mapping[str, object]]) -> dict[str, int]:
    outcomes: dict[str, int] = {}
    for item in results:
        classification = _mapping(_required(item, "classification"), "classification")
        outcome = _string(classification, "outcome")
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
    return dict(sorted(outcomes.items()))


def _validate_reference_comparison(
    result: Mapping[str, object], selected: HombergerSelection
) -> None:
    comparison = _mapping(_required(result, "reference_comparison"), "reference_comparison")
    if "reference_note" not in comparison:
        raise HombergerEvaluationError("run artifact reference lineage mismatch")
    allowed = _boolean(comparison, "comparison_allowed")
    status = _string(comparison, "status")
    if (
        allowed != selected.reference_comparison_allowed
        or _integer(comparison, "reference_vehicle_count") != selected.reference_vehicle_count
        or _number(comparison, "reference_distance") != selected.reference_distance
        or comparison.get("reference_note") != selected.reference_note
    ):
        raise HombergerEvaluationError("run artifact reference lineage mismatch")
    gap = comparison.get("distance_gap_percent")
    if not selected.reference_comparison_allowed:
        if status != "REFERENCE_QUALITY_REVIEW" or gap is not None:
            raise HombergerEvaluationError("withheld reference cannot receive a scalar gap")
    elif gap is not None:
        _number(comparison, "distance_gap_percent")
        if status != "COMPARABLE_SAME_VEHICLE_COUNT":
            raise HombergerEvaluationError("scalar gap requires an allowed same-vehicle comparison")


def _accepted(result: Mapping[str, object]) -> bool:
    classification = _mapping(_required(result, "classification"), "classification")
    return _boolean(classification, "accepted_feasible_incumbent")


def _result_scale(result: Mapping[str, object]) -> int:
    instance = _mapping(_required(result, "instance"), "instance")
    return _integer(instance, "customer_count")


def _routing_termination(status: str) -> tuple[SolverTermination, SolverProof, str | None]:
    if status in {
        "ROUTING_PARTIAL_SUCCESS_LOCAL_OPTIMUM_NOT_REACHED",
        "ROUTING_FAIL_TIMEOUT",
    }:
        return SolverTermination.WALL_TIME_LIMIT, SolverProof.NONE, None
    if status == "ROUTING_OPTIMAL":
        return SolverTermination.COMPLETED, SolverProof.OPTIMALITY, None
    if status == "ROUTING_INFEASIBLE":
        return SolverTermination.COMPLETED, SolverProof.INFEASIBILITY, None
    if status in _STATUS_ERROR:
        return SolverTermination.ERROR, SolverProof.NONE, f"ORTOOLS_{status}"
    if status in {"ROUTING_SUCCESS", "ROUTING_FAIL"}:
        return SolverTermination.COMPLETED, SolverProof.NONE, None
    return SolverTermination.ERROR, SolverProof.NONE, "ORTOOLS_STATUS_UNKNOWN"


def _solution_payload(solution: PublicVrptwSolution | None) -> dict[str, object] | None:
    if solution is None:
        return None
    return {
        "instance_id": solution.instance_id,
        "claimed_vehicle_count": solution.claimed_vehicle_count,
        "claimed_total_distance": solution.claimed_total_distance,
        "claimed_feasible": solution.claimed_feasible,
        "objective_semantics": solution.objective_semantics,
        "unassigned_node_ids": list(solution.unassigned_node_ids),
        "routes": [
            {
                "vehicle_id": route.vehicle_id,
                "claimed_distance": route.claimed_distance,
                "visits": [
                    {
                        "node_id": visit.node_id,
                        "arrival_time": visit.arrival_time,
                        "service_start_time": visit.service_start_time,
                        "departure_time": visit.departure_time,
                    }
                    for visit in route.visits
                ],
            }
            for route in solution.routes
        ],
    }


def _verification_payload(
    report: PublicVrptwVerificationReport | None,
) -> dict[str, object] | None:
    if report is None:
        return None
    return {
        "valid": report.valid,
        "complete": report.complete,
        "checks": list(report.checks),
        "issues": [issue.as_dict() for issue in report.issues],
        "recomputed_vehicle_count": report.recomputed_vehicle_count,
        "recomputed_total_distance": report.recomputed_total_distance,
    }


def _validated_output_directory(protocol: HombergerProtocol, data_root: Path, output: Path) -> Path:
    root = data_root.expanduser().resolve()
    allowed = (root / protocol.result_relative_root).resolve()
    target = output.expanduser().resolve()
    try:
        target.relative_to(allowed)
    except ValueError as exc:
        raise HombergerEvaluationError(
            "campaign output must remain below the frozen data root"
        ) from exc
    if target == allowed:
        raise HombergerEvaluationError("campaign output must use a distinct campaign directory")
    return target


def _read_verified_artifact(path: Path) -> Mapping[str, object]:
    try:
        raw = path.read_bytes()
        expected = path.with_suffix(path.suffix + ".sha256").read_text(encoding="ascii").strip()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HombergerEvaluationError(f"run artifact is unreadable: {path.name}") from exc
    if not _SHA256.fullmatch(expected) or sha256(raw).hexdigest() != expected:
        raise HombergerEvaluationError(f"run artifact checksum mismatch: {path.stem}")
    return _mapping(value, "run artifact")


def _write_json_once(path: Path, payload: Mapping[str, object]) -> Path:
    encoded = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    try:
        with path.open("xb") as stream:
            stream.write(encoded)
        path.with_suffix(path.suffix + ".sha256").write_text(
            sha256(encoded).hexdigest() + "\n", encoding="ascii"
        )
    except OSError as exc:
        raise HombergerEvaluationError(f"unable to write immutable artifact: {path.name}") from exc
    return path


def _archive(value: Mapping[str, object]) -> HombergerArchive:
    return HombergerArchive(
        customer_count=_positive_integer(value, "customer_count"),
        source_page_url=_string(value, "source_page_url"),
        download_url=_string(value, "download_url"),
        relative_path=_safe_relative_path(value, "relative_path"),
        bytes=_positive_integer(value, "bytes"),
        sha256=_digest(value, "sha256"),
        member_count=_positive_integer(value, "member_count"),
    )


def _selection(value: Mapping[str, object]) -> HombergerSelection:
    reference_distance = _number(value, "reference_distance")
    if reference_distance <= 0:
        raise HombergerEvaluationError("reference distance must be positive")
    allowed = _boolean(value, "reference_comparison_allowed")
    reference_note = value.get("reference_note")
    if reference_note is not None and (
        not isinstance(reference_note, str) or not reference_note.strip()
    ):
        raise HombergerEvaluationError("reference_note must be non-blank when present")
    if not allowed and reference_note is None:
        raise HombergerEvaluationError("withheld reference comparison requires a source note")
    return HombergerSelection(
        customer_count=_positive_integer(value, "customer_count"),
        family=_string(value, "family"),
        instance_id=_string(value, "instance_id"),
        archive_member=_safe_relative_path(value, "archive_member"),
        relative_path=_safe_relative_path(value, "relative_path"),
        sha256=_digest(value, "sha256"),
        reference_vehicle_count=_positive_integer(value, "reference_vehicle_count"),
        reference_distance=reference_distance,
        reference_status=_string(value, "reference_status"),
        reference_comparison_allowed=allowed,
        reference_note=reference_note,
    )


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise HombergerEvaluationError(f"{label} must be an object")
    return cast(Mapping[str, object], value)


def _sequence(value: object, label: str) -> Sequence[object]:
    if not isinstance(value, list):
        raise HombergerEvaluationError(f"{label} must be an array")
    return cast(Sequence[object], value)


def _required(value: Mapping[str, object], key: str) -> object:
    if key not in value:
        raise HombergerEvaluationError(f"{key} is required")
    return value[key]


def _string(value: Mapping[str, object], key: str) -> str:
    item = _required(value, key)
    if not isinstance(item, str) or not item.strip():
        raise HombergerEvaluationError(f"{key} must be a non-blank string")
    return item


def _safe_relative_path(value: Mapping[str, object], key: str) -> str:
    item = _string(value, key)
    path = PurePosixPath(item)
    if path.is_absolute() or "\\" in item or any(part in {"", ".."} for part in path.parts):
        raise HombergerEvaluationError(f"{key} must be a safe relative POSIX path")
    return item


def _boolean(value: Mapping[str, object], key: str) -> bool:
    item = _required(value, key)
    if not isinstance(item, bool):
        raise HombergerEvaluationError(f"{key} must be boolean")
    return item


def _integer(value: Mapping[str, object], key: str) -> int:
    item = _required(value, key)
    if not isinstance(item, int) or isinstance(item, bool):
        raise HombergerEvaluationError(f"{key} must be an integer")
    return item


def _positive_integer(value: Mapping[str, object], key: str) -> int:
    item = _integer(value, key)
    if item <= 0:
        raise HombergerEvaluationError(f"{key} must be positive")
    return item


def _number(value: Mapping[str, object], key: str) -> float:
    item = _required(value, key)
    if not isinstance(item, (int, float)) or isinstance(item, bool) or not isfinite(item):
        raise HombergerEvaluationError(f"{key} must be finite numeric")
    return float(item)


def _digest(value: Mapping[str, object], key: str) -> str:
    item = _string(value, key)
    if not _SHA256.fullmatch(item):
        raise HombergerEvaluationError(f"{key} must be a lowercase SHA-256 digest")
    return item


def _integer_array(value: Mapping[str, object], key: str) -> tuple[int, ...]:
    items = _sequence(_required(value, key), key)
    if any(not isinstance(item, int) or isinstance(item, bool) for item in items):
        raise HombergerEvaluationError(f"{key} must contain integers")
    return cast(tuple[int, ...], tuple(items))


def _string_array(value: Mapping[str, object], key: str) -> tuple[str, ...]:
    items = _sequence(_required(value, key), key)
    if any(not isinstance(item, str) or not item.strip() for item in items):
        raise HombergerEvaluationError(f"{key} must contain non-blank strings")
    return cast(tuple[str, ...], tuple(items))


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run frozen R3-312 Homberger evaluation")
    parser.add_argument("action", choices=("instance", "summarize"))
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--code-revision", required=True)
    parser.add_argument("--instance-id")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    if arguments.action == "instance":
        if arguments.instance_id is None:
            raise HombergerEvaluationError("instance action requires --instance-id")
        path = run_selected_instance(
            arguments.protocol,
            arguments.data_root,
            arguments.output_directory,
            arguments.instance_id,
            arguments.campaign_id,
            arguments.code_revision,
        )
    else:
        if arguments.instance_id is not None:
            raise HombergerEvaluationError("summarize action does not accept --instance-id")
        path = summarize_campaign(
            arguments.protocol,
            arguments.data_root,
            arguments.output_directory,
            arguments.campaign_id,
            arguments.code_revision,
        )
    print(path)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
