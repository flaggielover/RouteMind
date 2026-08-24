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
from math import ceil, hypot, isfinite, sqrt
from pathlib import Path
from time import perf_counter
from typing import cast

import ortools  # type: ignore[import-untyped]
from ortools.constraint_solver import pywrapcp, routing_enums_pb2  # type: ignore[import-untyped]

from routemind_compute.application.artifacts import (
    DataArtifactManifest,
    DataRootArtifactAdapter,
)
from routemind_compute.application.public_benchmarks import (
    BenchmarkReferenceValue,
    CanonicalVrptwInstance,
    CanonicalVrptwNode,
    LicenseStatus,
    ParsedPublicBenchmark,
    PublicBenchmarkSourceManifest,
    PublicVrptwRoute,
    PublicVrptwSolution,
    PublicVrptwVisit,
    ReferenceStatus,
    load_public_benchmark,
)
from routemind_compute.application.solver_outcomes import (
    ClassifiedSolverRun,
    SolverProof,
    SolverResourceLimits,
    SolverResourceUsage,
    SolverRunObservation,
    SolverTermination,
    classify_solver_run,
)
from routemind_compute.application.verification import (
    PublicVrptwVerificationReport,
    verify_public_vrptw_solution,
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REVISION = re.compile(r"^[0-9a-f]{40}$")
_SUPPORTED_SCHEMA = "routemind-solomon-experiment-v1"
_STATUS_ERROR = {"ROUTING_INVALID", "ROUTING_NOT_SOLVED"}


class SolomonEvaluationError(ValueError):
    """Raised when a frozen Solomon protocol or run artifact is invalid."""


@dataclass(frozen=True, slots=True)
class SolomonSource:
    family: str
    source_page_url: str
    download_url: str
    license_status: str
    distribution_sha256: str
    parser_id: str
    parser_version: str


@dataclass(frozen=True, slots=True)
class SolomonSelection:
    family: str
    instance_id: str
    archive_member: str
    relative_path: str
    sha256: str
    reference_vehicle_count: int
    reference_distance: float
    reference_status: str


@dataclass(frozen=True, slots=True)
class SolomonProtocol:
    manifest_id: str
    frozen_at_utc: str
    manifest_sha256: str
    source: SolomonSource
    instances: tuple[SolomonSelection, ...]
    solver_version: str
    seed: int
    wall_time_seconds: float
    threads: int
    integer_scale: int
    result_relative_root: str

    def selection(self, instance_id: str) -> SolomonSelection:
        matches = [item for item in self.instances if item.instance_id == instance_id]
        if len(matches) != 1:
            raise SolomonEvaluationError(f"instance {instance_id} is not uniquely selected")
        return matches[0]


@dataclass(frozen=True, slots=True)
class ReferenceComparison:
    status: str
    reference_vehicle_count: int
    reference_distance: float
    result_vehicle_count: int | None
    result_distance_2dp: float | None
    distance_gap_percent: float | None

    def payload(self) -> dict[str, object]:
        return {
            "status": self.status,
            "reference_vehicle_count": self.reference_vehicle_count,
            "reference_distance": self.reference_distance,
            "result_vehicle_count": self.result_vehicle_count,
            "result_distance_2dp": self.result_distance_2dp,
            "distance_gap_percent": self.distance_gap_percent,
        }


@dataclass(frozen=True, slots=True)
class SolomonSolverRun:
    run_id: str
    campaign_id: str
    code_revision: str
    started_at_utc: str
    completed_at_utc: str
    selection: SolomonSelection
    parsed: ParsedPublicBenchmark
    ortools_status_code: int
    ortools_status: str
    elapsed_seconds: float
    fixed_vehicle_cost: int
    solution: PublicVrptwSolution | None
    verification: PublicVrptwVerificationReport | None
    classified: ClassifiedSolverRun
    comparison: ReferenceComparison

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "routemind-solomon-run-v1",
            "run_id": self.run_id,
            "campaign_id": self.campaign_id,
            "code_revision": self.code_revision,
            "started_at_utc": self.started_at_utc,
            "completed_at_utc": self.completed_at_utc,
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "ortools": ortools.__version__,
            },
            "instance": {
                "family": self.selection.family,
                "instance_id": self.selection.instance_id,
                "archive_member": self.selection.archive_member,
                "artifact_sha256": self.parsed.artifact_sha256,
                "canonical_digest": self.parsed.instance.digest,
                "lineage_digest": self.parsed.lineage_digest,
            },
            "solver": {
                "name": "Google OR-Tools RoutingModel",
                "version": ortools.__version__,
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


def load_solomon_protocol(path: Path) -> SolomonProtocol:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SolomonEvaluationError("Solomon protocol is unreadable") from exc
    root = _mapping(value, "protocol")
    if _string(root, "schema_version") != _SUPPORTED_SCHEMA:
        raise SolomonEvaluationError("Solomon protocol schema is unsupported")
    if _boolean(root, "material_execution_started"):
        raise SolomonEvaluationError("frozen protocol must precede material execution")
    source_value = _mapping(_required(root, "source"), "source")
    selection_value = _mapping(_required(root, "selection"), "selection")
    solver_value = _mapping(_required(root, "solver"), "solver")
    resource_value = _mapping(_required(root, "resource_policy"), "resource_policy")
    modeling_value = _mapping(_required(root, "modeling"), "modeling")
    artifact_value = _mapping(_required(root, "artifact_policy"), "artifact_policy")
    instances = tuple(
        _selection(_mapping(item, "selected instance"))
        for item in _sequence(_required(selection_value, "instances"), "instances")
    )
    if _integer(selection_value, "selected_count") != len(instances):
        raise SolomonEvaluationError("selected_count does not match selected instances")
    if len(instances) != 6:
        raise SolomonEvaluationError("R3-311 protocol must retain exactly six instances")
    if len({item.family for item in instances}) != len(instances):
        raise SolomonEvaluationError("selected structural families must be unique")
    if len({item.instance_id for item in instances}) != len(instances):
        raise SolomonEvaluationError("selected instance identities must be unique")
    if _string(solver_value, "package") != "ortools":
        raise SolomonEvaluationError("R3-311 solver package must be ortools")
    wall_time = _number(resource_value, "wall_time_seconds_per_instance")
    if wall_time <= 0:
        raise SolomonEvaluationError("solver wall time must be positive")
    threads = _integer(resource_value, "threads")
    if threads != 1:
        raise SolomonEvaluationError("R3-311 requires one solver thread")
    integer_scale = _integer(modeling_value, "integer_scale")
    if integer_scale <= 0:
        raise SolomonEvaluationError("integer scale must be positive")
    source = SolomonSource(
        family=_string(source_value, "family"),
        source_page_url=_string(source_value, "source_page_url"),
        download_url=_string(source_value, "download_url"),
        license_status=_string(source_value, "license_status"),
        distribution_sha256=_digest(source_value, "distribution_sha256"),
        parser_id=_string(source_value, "parser_id"),
        parser_version=_string(source_value, "parser_version"),
    )
    protocol = SolomonProtocol(
        manifest_id=_string(root, "manifest_id"),
        frozen_at_utc=_string(root, "frozen_at_utc"),
        manifest_sha256=sha256(raw).hexdigest(),
        source=source,
        instances=instances,
        solver_version=_string(solver_value, "version"),
        seed=_integer(solver_value, "seed"),
        wall_time_seconds=wall_time,
        threads=threads,
        integer_scale=integer_scale,
        result_relative_root=_string(artifact_value, "result_relative_root"),
    )
    if protocol.solver_version != ortools.__version__:
        raise SolomonEvaluationError("installed OR-Tools version differs from frozen protocol")
    return protocol


def source_manifest(
    protocol: SolomonProtocol, selected: SolomonSelection
) -> PublicBenchmarkSourceManifest:
    artifact = DataArtifactManifest(
        artifact_id=f"solomon-{selected.instance_id.lower()}",
        artifact_type="benchmark",
        relative_path=selected.relative_path,
        sha256=selected.sha256,
        producer="SINTEF Solomon 100-customer backup archive",
        revision=f"sha256:{protocol.source.distribution_sha256}",
        configuration=(
            ("archive_member", selected.archive_member),
            ("distance_semantics", "EUCLIDEAN_DOUBLE"),
            ("objective_semantics", "HIERARCHICAL_VEHICLES_THEN_DISTANCE"),
        ),
        seed=protocol.seed,
    )
    reference = BenchmarkReferenceValue(
        reference_id=f"sintef-{selected.instance_id.lower()}-hierarchical-double-2026-08-24",
        instance_id=selected.instance_id,
        reference_status=cast(ReferenceStatus, selected.reference_status),
        vehicle_count=selected.reference_vehicle_count,
        distance=selected.reference_distance,
        objective_semantics="HIERARCHICAL_VEHICLES_THEN_DISTANCE",
        numeric_semantics="EUCLIDEAN_DOUBLE_DISTANCE_ROUNDED_2DP",
        source_url=protocol.source.source_page_url,
        notes="SINTEF hierarchical vehicle-count then double-distance reference.",
    )
    return PublicBenchmarkSourceManifest(
        source_id=f"{protocol.manifest_id}-{selected.instance_id.lower()}",
        family=protocol.source.family,
        instance_id=selected.instance_id,
        source_page_url=protocol.source.source_page_url,
        download_url=protocol.source.download_url,
        retrieved_at_utc=protocol.frozen_at_utc,
        license_status=cast(LicenseStatus, protocol.source.license_status),
        terms_url=protocol.source.source_page_url,
        redistribution_allowed=False,
        distribution_sha256=protocol.source.distribution_sha256,
        archive_member=selected.archive_member,
        parser_id=protocol.source.parser_id,
        parser_version=protocol.source.parser_version,
        artifact=artifact,
        references=(reference,),
    )


def solve_solomon_instance(
    protocol: SolomonProtocol,
    selected: SolomonSelection,
    parsed: ParsedPublicBenchmark,
    *,
    campaign_id: str,
    code_revision: str,
) -> SolomonSolverRun:
    if not _REVISION.fullmatch(code_revision):
        raise SolomonEvaluationError("code revision must be a full lowercase Git SHA")
    if parsed.instance.instance_id.casefold() != selected.instance_id.casefold():
        raise SolomonEvaluationError("parsed instance does not match selected instance")
    started_at = _utc_now()
    model = _build_model(parsed.instance, protocol.integer_scale)
    parameters = pywrapcp.DefaultRoutingSearchParameters()
    parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    parameters.time_limit.FromMilliseconds(round(protocol.wall_time_seconds * 1000))
    parameters.sat_parameters.num_search_workers = protocol.threads
    parameters.sat_parameters.random_seed = protocol.seed
    started = perf_counter()
    assignment = model.routing.SolveWithParameters(parameters)
    elapsed = perf_counter() - started
    status_code = int(model.routing.status())
    status_name = routing_enums_pb2.RoutingSearchStatus.Value.Name(status_code)
    solution = None if assignment is None else _extract_solution(model, assignment)
    verification = (
        None
        if solution is None
        else verify_public_vrptw_solution(parsed.instance, solution, require_complete=True)
    )
    termination, proof, failure_code = _termination(status_name)
    limits = SolverResourceLimits(
        wall_time_seconds=protocol.wall_time_seconds,
        threads=protocol.threads,
    )
    observation = SolverRunObservation(
        run_id=f"{campaign_id}:{selected.instance_id.lower()}",
        solver_name="Google OR-Tools RoutingModel",
        solver_version=ortools.__version__,
        termination=termination,
        proof=proof,
        usage=SolverResourceUsage(elapsed_seconds=elapsed),
        incumbent_present=solution is not None,
        verification_report=verification,
        failure_code=failure_code,
    )
    classified = classify_solver_run(observation, limits)
    comparison = compare_reference(selected, verification)
    return SolomonSolverRun(
        run_id=observation.run_id,
        campaign_id=campaign_id,
        code_revision=code_revision,
        started_at_utc=started_at,
        completed_at_utc=_utc_now(),
        selection=selected,
        parsed=parsed,
        ortools_status_code=status_code,
        ortools_status=status_name,
        elapsed_seconds=elapsed,
        fixed_vehicle_cost=model.fixed_vehicle_cost,
        solution=solution,
        verification=verification,
        classified=classified,
        comparison=comparison,
    )


def compare_reference(
    selected: SolomonSelection,
    verification: PublicVrptwVerificationReport | None,
) -> ReferenceComparison:
    if verification is None or not verification.valid or not verification.complete:
        return ReferenceComparison(
            "REFERENCE_GAP_NOT_APPLICABLE",
            selected.reference_vehicle_count,
            selected.reference_distance,
            None if verification is None else verification.recomputed_vehicle_count,
            None,
            None,
        )
    vehicles = verification.recomputed_vehicle_count
    distance = round(verification.recomputed_total_distance, 2)
    if vehicles > selected.reference_vehicle_count:
        status = "VEHICLE_COUNT_WORSE"
        gap = None
    elif vehicles < selected.reference_vehicle_count:
        status = "REFERENCE_CONTRADICTION_REVIEW"
        gap = None
    else:
        status = "COMPARABLE_SAME_VEHICLE_COUNT"
        gap = (distance - selected.reference_distance) / selected.reference_distance * 100
    return ReferenceComparison(
        status,
        selected.reference_vehicle_count,
        selected.reference_distance,
        vehicles,
        distance,
        gap,
    )


def wilson_interval(successes: int, total: int) -> tuple[float, float]:
    if isinstance(successes, bool) or isinstance(total, bool) or total <= 0:
        raise SolomonEvaluationError("Wilson counts must be non-boolean with positive total")
    if successes < 0 or successes > total:
        raise SolomonEvaluationError("Wilson successes must be between zero and total")
    z = 1.959963984540054
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    radius = z * sqrt((proportion * (1 - proportion) + z * z / (4 * total)) / total) / denominator
    return center - radius, center + radius


def run_selected_instance(
    protocol_path: Path,
    data_root: Path,
    output_directory: Path,
    instance_id: str,
    campaign_id: str,
    code_revision: str,
) -> Path:
    protocol = load_solomon_protocol(protocol_path)
    selected = protocol.selection(instance_id)
    parsed = load_public_benchmark(
        source_manifest(protocol, selected), DataRootArtifactAdapter(data_root)
    )
    run = solve_solomon_instance(
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
    protocol = load_solomon_protocol(protocol_path)
    if not _REVISION.fullmatch(code_revision):
        raise SolomonEvaluationError("code revision must be a full lowercase Git SHA")
    output = _validated_output_directory(protocol, data_root, output_directory)
    results: list[Mapping[str, object]] = []
    for selected in protocol.instances:
        path = output / f"{selected.instance_id.lower()}.json"
        raw = path.read_bytes()
        expected = (path.with_suffix(path.suffix + ".sha256")).read_text(encoding="ascii").strip()
        if sha256(raw).hexdigest() != expected:
            raise SolomonEvaluationError(f"run artifact checksum mismatch: {selected.instance_id}")
        result = _mapping(json.loads(raw), "run artifact")
        if _string(result, "campaign_id") != campaign_id:
            raise SolomonEvaluationError("run artifact campaign identity mismatch")
        if _string(result, "code_revision") != code_revision:
            raise SolomonEvaluationError("run artifact code revision mismatch")
        results.append(result)
    verified = sum(
        _boolean(
            _mapping(_required(item, "classification"), "classification"),
            "accepted_feasible_incumbent",
        )
        for item in results
    )
    lower, upper = wilson_interval(verified, len(results))
    outcomes: dict[str, int] = {}
    for item in results:
        classification = _mapping(_required(item, "classification"), "classification")
        outcome = _string(classification, "outcome")
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
    payload: dict[str, object] = {
        "schema_version": "routemind-solomon-campaign-summary-v1",
        "manifest_id": protocol.manifest_id,
        "manifest_sha256": protocol.manifest_sha256,
        "campaign_id": campaign_id,
        "code_revision": code_revision,
        "completed_at_utc": _utc_now(),
        "selected_count": len(results),
        "retained_count": len(results),
        "verified_complete_count": verified,
        "verified_complete_rate": verified / len(results),
        "wilson_95": {"lower": lower, "upper": upper},
        "frozen_success_gate": 0.95,
        "hypothesis_passed": lower >= 0.95,
        "statistical_disposition": "S-FAIL",
        "claim_disposition": "C-NO-CLAIM",
        "outcomes": dict(sorted(outcomes.items())),
        "artifacts": [f"{item.instance_id.lower()}.json" for item in protocol.instances],
    }
    return _write_json_once(output / "campaign-summary.json", payload)


@dataclass(frozen=True, slots=True)
class _OrtoolsModel:
    manager: pywrapcp.RoutingIndexManager
    routing: pywrapcp.RoutingModel
    instance: CanonicalVrptwInstance
    nodes: tuple[CanonicalVrptwNode, ...]
    fixed_vehicle_cost: int


def _build_model(instance: CanonicalVrptwInstance, scale: int) -> _OrtoolsModel:
    nodes = (instance.depot, *instance.customers)
    manager = pywrapcp.RoutingIndexManager(len(nodes), instance.max_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)
    arc_costs = tuple(
        tuple(
            ceil(
                hypot(destination.point.x - origin.point.x, destination.point.y - origin.point.y)
                * scale
            )
            for destination in nodes
        )
        for origin in nodes
    )
    services = tuple(_scaled_integer(node.service_time, scale, "service time") for node in nodes)
    demands = tuple(_source_integer(node.demand, "demand") for node in nodes)

    def distance_callback(from_index: int, to_index: int) -> int:
        source = int(manager.IndexToNode(from_index))
        destination = int(manager.IndexToNode(to_index))
        return arc_costs[source][destination]

    def time_callback(from_index: int, to_index: int) -> int:
        source = int(manager.IndexToNode(from_index))
        destination = int(manager.IndexToNode(to_index))
        return services[source] + arc_costs[source][destination]

    def demand_callback(from_index: int) -> int:
        return demands[int(manager.IndexToNode(from_index))]

    distance_index = routing.RegisterTransitCallback(distance_callback)
    time_index = routing.RegisterTransitCallback(time_callback)
    demand_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(distance_index)
    max_arc = max(max(row) for row in arc_costs)
    fixed_cost = max_arc * (len(instance.customers) + instance.max_vehicles) + 1
    routing.SetFixedCostOfAllVehicles(fixed_cost)
    horizon = _scaled_integer(instance.depot.due_time, scale, "depot due time")
    if not routing.AddDimension(time_index, horizon, horizon, False, "Time"):
        raise SolomonEvaluationError("OR-Tools rejected time dimension")
    time_dimension = routing.GetDimensionOrDie("Time")
    for position, node in enumerate(nodes):
        index = manager.NodeToIndex(position)
        time_dimension.CumulVar(index).SetRange(
            _scaled_integer(node.ready_time, scale, "ready time"),
            _scaled_integer(node.due_time, scale, "due time"),
        )
    depot_ready = _scaled_integer(instance.depot.ready_time, scale, "depot ready time")
    for vehicle in range(instance.max_vehicles):
        time_dimension.CumulVar(routing.Start(vehicle)).SetRange(depot_ready, horizon)
        time_dimension.CumulVar(routing.End(vehicle)).SetRange(depot_ready, horizon)
    capacity = _source_integer(instance.vehicle_capacity, "vehicle capacity")
    if not routing.AddDimensionWithVehicleCapacity(
        demand_index,
        0,
        [capacity] * instance.max_vehicles,
        True,
        "Capacity",
    ):
        raise SolomonEvaluationError("OR-Tools rejected capacity dimension")
    return _OrtoolsModel(manager, routing, instance, nodes, fixed_cost)


def _extract_solution(model: _OrtoolsModel, assignment: pywrapcp.Assignment) -> PublicVrptwSolution:
    routes: list[PublicVrptwRoute] = []
    for vehicle in range(model.instance.max_vehicles):
        index = model.routing.Start(vehicle)
        node_ids: list[int] = []
        while not model.routing.IsEnd(index):
            node_ids.append(model.nodes[model.manager.IndexToNode(index)].node_id)
            index = assignment.Value(model.routing.NextVar(index))
        node_ids.append(model.nodes[model.manager.IndexToNode(index)].node_id)
        if len(node_ids) == 2:
            continue
        route = _exact_route(model.instance, vehicle, tuple(node_ids))
        routes.append(route)
    total_distance = sum(route.claimed_distance for route in routes)
    return PublicVrptwSolution(
        instance_id=model.instance.instance_id,
        routes=tuple(routes),
        unassigned_node_ids=(),
        claimed_vehicle_count=len(routes),
        claimed_total_distance=total_distance,
        claimed_feasible=True,
        objective_semantics=model.instance.objective_semantics,
    )


def _exact_route(
    instance: CanonicalVrptwInstance,
    vehicle: int,
    node_ids: tuple[int, ...],
) -> PublicVrptwRoute:
    by_id = {instance.depot.node_id: instance.depot}
    by_id.update({node.node_id: node for node in instance.customers})
    visits: list[PublicVrptwVisit] = []
    previous: CanonicalVrptwNode | None = None
    previous_departure = 0.0
    distance = 0.0
    for node_id in node_ids:
        node = by_id[node_id]
        if previous is None:
            arrival = node.ready_time
        else:
            leg = hypot(node.point.x - previous.point.x, node.point.y - previous.point.y)
            distance += leg
            arrival = previous_departure + leg
        service_start = max(arrival, node.ready_time)
        departure = service_start + node.service_time
        visits.append(PublicVrptwVisit(node_id, arrival, service_start, departure))
        previous = node
        previous_departure = departure
    return PublicVrptwRoute(f"vehicle-{vehicle + 1:02d}", tuple(visits), distance)


def _termination(status: str) -> tuple[SolverTermination, SolverProof, str | None]:
    if status == "ROUTING_PARTIAL_SUCCESS_LOCAL_OPTIMUM_NOT_REACHED":
        return SolverTermination.WALL_TIME_LIMIT, SolverProof.NONE, None
    if status == "ROUTING_FAIL_TIMEOUT":
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


def _validated_output_directory(protocol: SolomonProtocol, data_root: Path, output: Path) -> Path:
    root = data_root.expanduser().resolve()
    allowed = (root / protocol.result_relative_root).resolve()
    target = output.expanduser().resolve()
    try:
        target.relative_to(allowed)
    except ValueError as exc:
        raise SolomonEvaluationError(
            "campaign output must remain below the frozen data root"
        ) from exc
    if target == allowed:
        raise SolomonEvaluationError("campaign output must use a distinct campaign directory")
    return target


def _write_json_once(path: Path, payload: Mapping[str, object]) -> Path:
    encoded = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    try:
        with path.open("xb") as stream:
            stream.write(encoded)
        path.with_suffix(path.suffix + ".sha256").write_text(
            sha256(encoded).hexdigest() + "\n", encoding="ascii"
        )
    except OSError as exc:
        raise SolomonEvaluationError(f"unable to write immutable artifact: {path.name}") from exc
    return path


def _selection(value: Mapping[str, object]) -> SolomonSelection:
    reference_distance = _number(value, "reference_distance")
    if reference_distance <= 0:
        raise SolomonEvaluationError("reference distance must be positive")
    return SolomonSelection(
        family=_string(value, "family"),
        instance_id=_string(value, "instance_id"),
        archive_member=_string(value, "archive_member"),
        relative_path=_string(value, "relative_path"),
        sha256=_digest(value, "sha256"),
        reference_vehicle_count=_positive_integer(value, "reference_vehicle_count"),
        reference_distance=reference_distance,
        reference_status=_string(value, "reference_status"),
    )


def _scaled_integer(value: float, scale: int, label: str) -> int:
    scaled = value * scale
    if not isfinite(scaled) or abs(scaled - round(scaled)) > 1e-9:
        raise SolomonEvaluationError(f"{label} cannot be represented at frozen scale")
    return round(scaled)


def _source_integer(value: float, label: str) -> int:
    if not isfinite(value) or abs(value - round(value)) > 1e-9:
        raise SolomonEvaluationError(f"{label} must preserve an integer source value")
    return round(value)


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise SolomonEvaluationError(f"{label} must be an object")
    return cast(Mapping[str, object], value)


def _sequence(value: object, label: str) -> Sequence[object]:
    if not isinstance(value, list):
        raise SolomonEvaluationError(f"{label} must be an array")
    return cast(Sequence[object], value)


def _required(value: Mapping[str, object], key: str) -> object:
    if key not in value:
        raise SolomonEvaluationError(f"{key} is required")
    return value[key]


def _string(value: Mapping[str, object], key: str) -> str:
    item = _required(value, key)
    if not isinstance(item, str) or not item.strip():
        raise SolomonEvaluationError(f"{key} must be a non-blank string")
    return item


def _boolean(value: Mapping[str, object], key: str) -> bool:
    item = _required(value, key)
    if not isinstance(item, bool):
        raise SolomonEvaluationError(f"{key} must be boolean")
    return item


def _integer(value: Mapping[str, object], key: str) -> int:
    item = _required(value, key)
    if not isinstance(item, int) or isinstance(item, bool):
        raise SolomonEvaluationError(f"{key} must be an integer")
    return item


def _positive_integer(value: Mapping[str, object], key: str) -> int:
    item = _integer(value, key)
    if item <= 0:
        raise SolomonEvaluationError(f"{key} must be positive")
    return item


def _number(value: Mapping[str, object], key: str) -> float:
    item = _required(value, key)
    if not isinstance(item, (int, float)) or isinstance(item, bool) or not isfinite(item):
        raise SolomonEvaluationError(f"{key} must be finite numeric")
    return float(item)


def _digest(value: Mapping[str, object], key: str) -> str:
    item = _string(value, key)
    if not _SHA256.fullmatch(item):
        raise SolomonEvaluationError(f"{key} must be a lowercase SHA-256 digest")
    return item


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run frozen R3-311 Solomon evaluation")
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
            raise SolomonEvaluationError("instance action requires --instance-id")
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
            raise SolomonEvaluationError("summarize action does not accept --instance-id")
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
