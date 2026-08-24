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
from math import ceil, hypot, isfinite
from pathlib import Path
from time import perf_counter

from ortools.sat.python import cp_model

from routemind_compute.application.artifacts import DataRootArtifactAdapter
from routemind_compute.application.public_benchmarks import (
    CanonicalVrptwInstance,
    CanonicalVrptwNode,
    ParsedPublicBenchmark,
    PublicVrptwRoute,
    PublicVrptwSolution,
    PublicVrptwVisit,
    load_public_benchmark,
)
from routemind_compute.application.solomon_evaluation import (
    CanonicalRoutingRun,
    SolomonProtocol,
    load_solomon_protocol,
    solve_canonical_vrptw,
    source_manifest,
)
from routemind_compute.application.verification import (
    PublicVrptwVerificationReport,
    verify_public_vrptw_solution,
)

_SCHEMA = "routemind-exact-cross-check-experiment-v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REVISION = re.compile(r"^[0-9a-f]{40}$")
_ORTOOLS_VERSION = version("ortools")


class ExactCrossCheckError(ValueError):
    """Raised when the frozen exact cross-check contract cannot be honored."""


@dataclass(frozen=True, slots=True)
class ExactSelection:
    family: str
    source_instance_id: str
    derived_instance_id: str
    source_sha256: str


@dataclass(frozen=True, slots=True)
class ExactProtocol:
    manifest_id: str
    manifest_sha256: str
    source_protocol_sha256: str
    selections: tuple[ExactSelection, ...]
    customer_count: int
    integer_scale: int
    candidate_wall_time_seconds: float
    exact_wall_time_seconds: float
    threads: int
    seed: int
    enumeration_sequence_ceiling: int
    result_relative_root: str

    def selection(self, instance_id: str) -> ExactSelection:
        matches = [
            item
            for item in self.selections
            if item.source_instance_id.casefold() == instance_id.casefold()
        ]
        if len(matches) != 1:
            raise ExactCrossCheckError(f"instance {instance_id} is not uniquely selected")
        return matches[0]


@dataclass(frozen=True, slots=True)
class FeasibleRouteColumn:
    customer_ids: tuple[int, ...]
    customer_mask: int
    transformed_distance: int


@dataclass(frozen=True, slots=True)
class RouteEnumeration:
    columns: tuple[FeasibleRouteColumn, ...]
    examined_sequences: int
    elapsed_seconds: float
    complete: bool


@dataclass(frozen=True, slots=True)
class ExactSolve:
    status_code: int
    status: str
    elapsed_seconds: float
    objective_value: int | None
    best_objective_bound: int | None
    fixed_vehicle_cost: int
    selected_columns: tuple[FeasibleRouteColumn, ...]
    solution: PublicVrptwSolution | None
    verification: PublicVrptwVerificationReport | None
    ground_truth_status: str


def load_exact_protocol(path: Path) -> ExactProtocol:
    try:
        raw = path.read_bytes()
        root = _mapping(json.loads(raw), "protocol")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExactCrossCheckError("exact cross-check protocol is unreadable") from exc
    if _string(root, "schema_version") != _SCHEMA:
        raise ExactCrossCheckError("exact cross-check protocol schema is unsupported")
    if _boolean(root, "material_execution_started"):
        raise ExactCrossCheckError("frozen protocol must precede material execution")
    source = _mapping(_required(root, "source_protocol"), "source_protocol")
    selection = _mapping(_required(root, "selection"), "selection")
    modeling = _mapping(_required(root, "modeling"), "modeling")
    candidate = _mapping(_required(root, "candidate_solver"), "candidate_solver")
    exact = _mapping(_required(root, "exact_reference_solver"), "exact_reference_solver")
    artifacts = _mapping(_required(root, "artifact_policy"), "artifact_policy")
    selections = tuple(
        _exact_selection(_mapping(item, "selected instance"))
        for item in _sequence(_required(selection, "instances"), "instances")
    )
    if _integer(selection, "selected_count") != len(selections) or len(selections) != 6:
        raise ExactCrossCheckError("R3-315 must retain exactly six selections")
    if len({item.source_instance_id for item in selections}) != len(selections):
        raise ExactCrossCheckError("source instance identities must be unique")
    if _string(candidate, "version") != _ORTOOLS_VERSION:
        raise ExactCrossCheckError("candidate OR-Tools version differs from frozen protocol")
    if _string(exact, "version") != _ORTOOLS_VERSION:
        raise ExactCrossCheckError("exact OR-Tools version differs from frozen protocol")
    if _string(exact, "required_proof_status") != "OPTIMAL":
        raise ExactCrossCheckError("R3-315 requires an OPTIMAL exact proof")
    customer_count = _integer(selection, "customer_count")
    scale = _integer(modeling, "integer_scale")
    candidate_time = _number(candidate, "wall_time_seconds_per_instance")
    exact_time = _number(exact, "wall_time_seconds_per_instance")
    threads = _integer(exact, "threads")
    if customer_count != 8 or scale <= 0 or candidate_time <= 0 or exact_time <= 0:
        raise ExactCrossCheckError("frozen R3-315 size, scale, or time limit is invalid")
    if threads != 1 or _integer(candidate, "threads") != 1:
        raise ExactCrossCheckError("R3-315 requires one thread for both solver paths")
    if _integer(candidate, "sat_random_seed") != _integer(exact, "random_seed"):
        raise ExactCrossCheckError("candidate and exact seed policies differ")
    return ExactProtocol(
        manifest_id=_string(root, "manifest_id"),
        manifest_sha256=sha256(raw).hexdigest(),
        source_protocol_sha256=_digest(source, "sha256"),
        selections=selections,
        customer_count=customer_count,
        integer_scale=scale,
        candidate_wall_time_seconds=candidate_time,
        exact_wall_time_seconds=exact_time,
        threads=threads,
        seed=_integer(exact, "random_seed"),
        enumeration_sequence_ceiling=_integer(exact, "enumeration_sequence_ceiling_per_instance"),
        result_relative_root=_string(artifacts, "result_relative_root"),
    )


def derive_prefix_instance(
    parsed: ParsedPublicBenchmark, selection: ExactSelection, customer_count: int
) -> CanonicalVrptwInstance:
    source = parsed.instance
    if source.instance_id.casefold() != selection.source_instance_id.casefold():
        raise ExactCrossCheckError("source instance identity does not match frozen selection")
    if parsed.artifact_sha256 != selection.source_sha256:
        raise ExactCrossCheckError("source artifact hash does not match frozen selection")
    customers = tuple(sorted(source.customers, key=lambda item: item.node_id)[:customer_count])
    if len(customers) != customer_count:
        raise ExactCrossCheckError("source instance has too few customers for frozen derivation")
    return CanonicalVrptwInstance(
        instance_id=selection.derived_instance_id,
        max_vehicles=min(source.max_vehicles, customer_count),
        vehicle_capacity=source.vehicle_capacity,
        depot=source.depot,
        customers=customers,
        distance_semantics=source.distance_semantics,
        travel_time_semantics=source.travel_time_semantics,
        objective_semantics=source.objective_semantics,
    )


def enumerate_feasible_routes(
    instance: CanonicalVrptwInstance, *, scale: int, sequence_ceiling: int
) -> RouteEnumeration:
    if scale <= 0 or sequence_ceiling <= 0:
        raise ExactCrossCheckError("enumeration limits must be positive")
    started = perf_counter()
    nodes = (instance.depot, *instance.customers)
    arcs = _arc_costs(nodes, scale)
    ready = tuple(_scaled(node.ready_time, scale, "ready time") for node in nodes)
    due = tuple(_scaled(node.due_time, scale, "due time") for node in nodes)
    service = tuple(_scaled(node.service_time, scale, "service time") for node in nodes)
    demands = tuple(_integer_source(node.demand, "demand") for node in nodes)
    capacity = _integer_source(instance.vehicle_capacity, "vehicle capacity")
    examined = 0
    columns: list[FeasibleRouteColumn] = []
    all_customers = (1 << len(instance.customers)) - 1

    def visit(
        last: int,
        remaining: int,
        departure: int,
        load: int,
        distance: int,
        route: tuple[int, ...],
    ) -> None:
        nonlocal examined
        for offset, customer in enumerate(instance.customers, start=1):
            bit = 1 << (offset - 1)
            if not remaining & bit:
                continue
            examined += 1
            if examined > sequence_ceiling:
                raise ExactCrossCheckError("route enumeration exceeded the frozen sequence ceiling")
            next_load = load + demands[offset]
            arrival = departure + arcs[last][offset]
            service_start = max(arrival, ready[offset])
            next_departure = service_start + service[offset]
            if next_load > capacity or service_start > due[offset]:
                continue
            return_arrival = next_departure + arcs[offset][0]
            if return_arrival > due[0]:
                continue
            next_route = (*route, customer.node_id)
            next_distance = distance + arcs[last][offset]
            columns.append(
                FeasibleRouteColumn(
                    next_route, all_customers ^ (remaining ^ bit), next_distance + arcs[offset][0]
                )
            )
            visit(
                offset,
                remaining ^ bit,
                next_departure,
                next_load,
                next_distance,
                next_route,
            )

    visit(0, all_customers, ready[0] + service[0], 0, 0, ())
    columns.sort(key=lambda item: (item.customer_mask, item.customer_ids))
    return RouteEnumeration(tuple(columns), examined, perf_counter() - started, True)


def solve_exact_set_partition(
    instance: CanonicalVrptwInstance,
    enumeration: RouteEnumeration,
    *,
    scale: int,
    wall_time_seconds: float,
    threads: int,
    seed: int,
) -> ExactSolve:
    if not enumeration.complete:
        raise ExactCrossCheckError("incomplete enumeration cannot enter the exact solver")
    if wall_time_seconds <= 0 or threads != 1:
        raise ExactCrossCheckError("exact solver limits are invalid")
    max_arc = max(max(row) for row in _arc_costs((instance.depot, *instance.customers), scale))
    fixed_cost = max_arc * (len(instance.customers) + instance.max_vehicles) + 1
    model = cp_model.CpModel()
    variables = [
        model.new_bool_var(f"route_{index:06d}") for index in range(len(enumeration.columns))
    ]
    for customer_offset in range(len(instance.customers)):
        covering = [
            variable
            for variable, column in zip(variables, enumeration.columns, strict=True)
            if column.customer_mask & (1 << customer_offset)
        ]
        model.add_exactly_one(covering)
    model.add(sum(variables) <= instance.max_vehicles)
    model.minimize(
        sum(
            variable * (fixed_cost + column.transformed_distance)
            for variable, column in zip(variables, enumeration.columns, strict=True)
        )
    )
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = wall_time_seconds
    solver.parameters.num_search_workers = threads
    solver.parameters.random_seed = seed
    started = perf_counter()
    status_code = solver.solve(model)
    elapsed = perf_counter() - started
    status = solver.status_name(status_code)
    has_incumbent = status in {"OPTIMAL", "FEASIBLE"}
    selected = tuple(
        column
        for variable, column in zip(variables, enumeration.columns, strict=True)
        if has_incumbent and solver.boolean_value(variable)
    )
    solution = _solution_from_columns(instance, selected) if has_incumbent else None
    verification = (
        verify_public_vrptw_solution(instance, solution, require_complete=True)
        if solution is not None
        else None
    )
    proven = bool(
        status == "OPTIMAL"
        and verification is not None
        and verification.valid
        and verification.complete
    )
    return ExactSolve(
        status_code=int(status_code),
        status=status,
        elapsed_seconds=elapsed,
        objective_value=round(solver.objective_value) if has_incumbent else None,
        best_objective_bound=round(solver.best_objective_bound) if has_incumbent else None,
        fixed_vehicle_cost=fixed_cost,
        selected_columns=selected,
        solution=solution,
        verification=verification,
        ground_truth_status=(
            "TRANSFORMED_MODEL_GROUND_TRUTH" if proven else "OPTIMALITY_NOT_PROVEN"
        ),
    )


def compare_candidate(
    instance: CanonicalVrptwInstance,
    candidate: CanonicalRoutingRun,
    exact: ExactSolve,
    scale: int,
) -> dict[str, object]:
    candidate_verified = candidate.verification
    exact_verified = exact.verification
    if (
        exact.ground_truth_status != "TRANSFORMED_MODEL_GROUND_TRUTH"
        or candidate.solution is None
        or candidate_verified is None
        or not candidate_verified.valid
        or not candidate_verified.complete
        or exact.solution is None
        or exact_verified is None
    ):
        return {
            "status": "GAP_NOT_APPLICABLE",
            "vehicle_count_gap": None,
            "transformed_distance_gap_percent": None,
        }
    vehicle_gap = (
        candidate_verified.recomputed_vehicle_count - exact_verified.recomputed_vehicle_count
    )
    if vehicle_gap:
        return {
            "status": "VEHICLE_COUNT_DIFFERENCE",
            "vehicle_count_gap": vehicle_gap,
            "transformed_distance_gap_percent": None,
        }
    candidate_distance = _transformed_solution_distance(instance, candidate.solution, scale)
    exact_distance = sum(column.transformed_distance for column in exact.selected_columns)
    return {
        "status": "COMPARABLE_SAME_VEHICLE_COUNT",
        "vehicle_count_gap": 0,
        "candidate_transformed_distance": candidate_distance,
        "exact_transformed_distance": exact_distance,
        "transformed_distance_gap_percent": (candidate_distance - exact_distance)
        / exact_distance
        * 100,
    }


def execute_cross_check(
    protocol: ExactProtocol,
    source_protocol: SolomonProtocol,
    parsed: ParsedPublicBenchmark,
    selection: ExactSelection,
    *,
    campaign_id: str,
    code_revision: str,
) -> dict[str, object]:
    if not _REVISION.fullmatch(code_revision):
        raise ExactCrossCheckError("code revision must be a full lowercase Git SHA")
    instance = derive_prefix_instance(parsed, selection, protocol.customer_count)
    started_at = _utc_now()
    candidate = solve_canonical_vrptw(
        instance,
        integer_scale=protocol.integer_scale,
        wall_time_seconds=protocol.candidate_wall_time_seconds,
        threads=protocol.threads,
        seed=protocol.seed,
    )
    enumeration = enumerate_feasible_routes(
        instance,
        scale=protocol.integer_scale,
        sequence_ceiling=protocol.enumeration_sequence_ceiling,
    )
    exact = solve_exact_set_partition(
        instance,
        enumeration,
        scale=protocol.integer_scale,
        wall_time_seconds=protocol.exact_wall_time_seconds,
        threads=protocol.threads,
        seed=protocol.seed,
    )
    return {
        "schema_version": "routemind-exact-cross-check-run-v1",
        "run_id": f"{campaign_id}:{selection.source_instance_id.lower()}",
        "campaign_id": campaign_id,
        "code_revision": code_revision,
        "started_at_utc": started_at,
        "completed_at_utc": _utc_now(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "ortools": _ORTOOLS_VERSION,
        },
        "protocol": {
            "manifest_id": protocol.manifest_id,
            "manifest_sha256": protocol.manifest_sha256,
            "source_manifest_id": source_protocol.manifest_id,
            "source_manifest_sha256": source_protocol.manifest_sha256,
        },
        "instance": {
            "family": selection.family,
            "source_instance_id": selection.source_instance_id,
            "derived_instance_id": selection.derived_instance_id,
            "source_artifact_sha256": parsed.artifact_sha256,
            "source_instance_digest": parsed.instance.digest,
            "derived_instance_digest": instance.digest,
            "source_lineage_digest": parsed.lineage_digest,
            "customer_ids": [node.node_id for node in instance.customers],
            "customer_count": len(instance.customers),
            "max_vehicles": instance.max_vehicles,
        },
        "candidate": _candidate_payload(candidate, instance, protocol),
        "enumeration": {
            "complete": enumeration.complete,
            "examined_sequences": enumeration.examined_sequences,
            "sequence_ceiling": protocol.enumeration_sequence_ceiling,
            "feasible_route_columns": len(enumeration.columns),
            "elapsed_seconds": enumeration.elapsed_seconds,
            "columns_digest": _columns_digest(enumeration.columns),
        },
        "exact_reference": _exact_payload(exact, protocol),
        "comparison": compare_candidate(instance, candidate, exact, protocol.integer_scale),
        "claim_scope": {
            "supported": (
                "Exact status and gap apply to the frozen derived conservative integer model only."
            ),
            "source_double_optimality_proven": False,
            "source_100_customer_optimality_proven": False,
        },
    }


def run_selected_instance(
    protocol_path: Path,
    source_protocol_path: Path,
    data_root: Path,
    output_directory: Path,
    instance_id: str,
    campaign_id: str,
    code_revision: str,
) -> Path:
    protocol = load_exact_protocol(protocol_path)
    source_bytes = source_protocol_path.read_bytes()
    if sha256(source_bytes).hexdigest() != protocol.source_protocol_sha256:
        raise ExactCrossCheckError("source protocol checksum differs from frozen reference")
    source_protocol = load_solomon_protocol(source_protocol_path)
    selection = protocol.selection(instance_id)
    source_selection = source_protocol.selection(selection.source_instance_id)
    parsed = load_public_benchmark(
        source_manifest(source_protocol, source_selection), DataRootArtifactAdapter(data_root)
    )
    payload = execute_cross_check(
        protocol,
        source_protocol,
        parsed,
        selection,
        campaign_id=campaign_id,
        code_revision=code_revision,
    )
    output = _validated_output_directory(protocol, data_root, output_directory)
    output.mkdir(parents=True, exist_ok=True)
    return _write_json_once(output / f"{selection.source_instance_id.lower()}.json", payload)


def summarize_campaign(
    protocol_path: Path,
    data_root: Path,
    output_directory: Path,
    campaign_id: str,
    code_revision: str,
) -> Path:
    protocol = load_exact_protocol(protocol_path)
    if not _REVISION.fullmatch(code_revision):
        raise ExactCrossCheckError("code revision must be a full lowercase Git SHA")
    output = _validated_output_directory(protocol, data_root, output_directory)
    runs: list[Mapping[str, object]] = []
    for selection in protocol.selections:
        path = output / f"{selection.source_instance_id.lower()}.json"
        raw = path.read_bytes()
        digest = path.with_suffix(path.suffix + ".sha256").read_text(encoding="ascii").strip()
        if sha256(raw).hexdigest() != digest:
            raise ExactCrossCheckError("cross-check artifact checksum mismatch")
        run = _mapping(json.loads(raw), "run artifact")
        if (
            _string(run, "campaign_id") != campaign_id
            or _string(run, "code_revision") != code_revision
        ):
            raise ExactCrossCheckError("cross-check artifact campaign identity mismatch")
        runs.append(run)
    ground_truth_count = sum(
        _string(
            _mapping(_required(run, "exact_reference"), "exact reference"), "ground_truth_status"
        )
        == "TRANSFORMED_MODEL_GROUND_TRUTH"
        for run in runs
    )
    comparable_count = sum(
        _string(_mapping(_required(run, "comparison"), "comparison"), "status")
        == "COMPARABLE_SAME_VEHICLE_COUNT"
        for run in runs
    )
    payload: dict[str, object] = {
        "schema_version": "routemind-exact-cross-check-summary-v1",
        "manifest_id": protocol.manifest_id,
        "manifest_sha256": protocol.manifest_sha256,
        "campaign_id": campaign_id,
        "code_revision": code_revision,
        "completed_at_utc": _utc_now(),
        "selected_count": len(runs),
        "retained_count": len(runs),
        "transformed_ground_truth_count": ground_truth_count,
        "comparable_same_vehicle_count": comparable_count,
        "statistical_disposition": "S-NOT-APPLICABLE",
        "claim_disposition": "C-NO-CLAIM",
        "artifacts": [f"{item.source_instance_id.lower()}.json" for item in protocol.selections],
    }
    return _write_json_once(output / "campaign-summary.json", payload)


def _candidate_payload(
    run: CanonicalRoutingRun, instance: CanonicalVrptwInstance, protocol: ExactProtocol
) -> dict[str, object]:
    return {
        "solver": "Google OR-Tools RoutingModel",
        "version": _ORTOOLS_VERSION,
        "status_code": run.status_code,
        "status": run.status,
        "elapsed_seconds": run.elapsed_seconds,
        "wall_time_limit_seconds": protocol.candidate_wall_time_seconds,
        "threads": protocol.threads,
        "fixed_vehicle_cost": run.fixed_vehicle_cost,
        "transformed_distance": (
            None
            if run.solution is None
            else _transformed_solution_distance(instance, run.solution, protocol.integer_scale)
        ),
        "solution": _solution_payload(run.solution),
        "verification": _verification_payload(run.verification),
    }


def _exact_payload(exact: ExactSolve, protocol: ExactProtocol) -> dict[str, object]:
    return {
        "solver": "Exhaustive feasible-route enumeration plus OR-Tools CP-SAT set partitioning",
        "version": _ORTOOLS_VERSION,
        "status_code": exact.status_code,
        "status": exact.status,
        "elapsed_seconds": exact.elapsed_seconds,
        "wall_time_limit_seconds": protocol.exact_wall_time_seconds,
        "threads": protocol.threads,
        "random_seed": protocol.seed,
        "objective_value": exact.objective_value,
        "best_objective_bound": exact.best_objective_bound,
        "fixed_vehicle_cost": exact.fixed_vehicle_cost,
        "selected_route_count": len(exact.selected_columns),
        "transformed_distance": sum(item.transformed_distance for item in exact.selected_columns),
        "ground_truth_status": exact.ground_truth_status,
        "proof_scope": "DERIVED_CONSERVATIVE_INTEGER_MODEL_ONLY",
        "solution": _solution_payload(exact.solution),
        "verification": _verification_payload(exact.verification),
    }


def _solution_from_columns(
    instance: CanonicalVrptwInstance, columns: Sequence[FeasibleRouteColumn]
) -> PublicVrptwSolution:
    routes = tuple(
        _public_route(instance, index, (0, *column.customer_ids, 0))
        for index, column in enumerate(sorted(columns, key=lambda item: item.customer_ids), start=1)
    )
    return PublicVrptwSolution(
        instance_id=instance.instance_id,
        routes=routes,
        unassigned_node_ids=(),
        claimed_vehicle_count=len(routes),
        claimed_total_distance=sum(route.claimed_distance for route in routes),
        claimed_feasible=True,
        objective_semantics=instance.objective_semantics,
    )


def _public_route(
    instance: CanonicalVrptwInstance, vehicle: int, node_ids: tuple[int, ...]
) -> PublicVrptwRoute:
    by_id = {
        instance.depot.node_id: instance.depot,
        **{node.node_id: node for node in instance.customers},
    }
    visits: list[PublicVrptwVisit] = []
    previous: CanonicalVrptwNode | None = None
    departure = 0.0
    distance = 0.0
    for node_id in node_ids:
        node = by_id[node_id]
        arrival = node.ready_time if previous is None else departure + _distance(previous, node)
        if previous is not None:
            distance += _distance(previous, node)
        service_start = max(arrival, node.ready_time)
        departure = service_start + node.service_time
        visits.append(PublicVrptwVisit(node_id, arrival, service_start, departure))
        previous = node
    return PublicVrptwRoute(f"exact-{vehicle:02d}", tuple(visits), distance)


def _transformed_solution_distance(
    instance: CanonicalVrptwInstance,
    solution: PublicVrptwSolution,
    scale: int,
) -> int:
    by_id = {
        instance.depot.node_id: instance.depot,
        **{node.node_id: node for node in instance.customers},
    }
    return sum(
        ceil(_distance(by_id[first.node_id], by_id[second.node_id]) * scale)
        for route in solution.routes
        for first, second in zip(route.visits, route.visits[1:], strict=False)
    )


def _arc_costs(nodes: Sequence[CanonicalVrptwNode], scale: int) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(ceil(_distance(origin, destination) * scale) for destination in nodes)
        for origin in nodes
    )


def _distance(origin: CanonicalVrptwNode, destination: CanonicalVrptwNode) -> float:
    return hypot(destination.point.x - origin.point.x, destination.point.y - origin.point.y)


def _columns_digest(columns: Sequence[FeasibleRouteColumn]) -> str:
    value = [
        [list(column.customer_ids), column.customer_mask, column.transformed_distance]
        for column in columns
    ]
    return sha256(json.dumps(value, separators=(",", ":")).encode()).hexdigest()


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


def _validated_output_directory(protocol: ExactProtocol, data_root: Path, output: Path) -> Path:
    root = data_root.expanduser().resolve()
    allowed = (root / protocol.result_relative_root).resolve()
    target = output.expanduser().resolve()
    try:
        target.relative_to(allowed)
    except ValueError as exc:
        raise ExactCrossCheckError(
            "campaign output must remain below the frozen data root"
        ) from exc
    if target == allowed:
        raise ExactCrossCheckError("campaign output must use a distinct campaign directory")
    return target


def _write_json_once(path: Path, payload: Mapping[str, object]) -> Path:
    encoded = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    try:
        with path.open("xb") as stream:
            stream.write(encoded)
        with path.with_suffix(path.suffix + ".sha256").open("x", encoding="ascii") as stream:
            stream.write(f"{sha256(encoded).hexdigest()}\n")
    except FileExistsError as exc:
        raise ExactCrossCheckError("immutable cross-check artifact already exists") from exc
    return path


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _scaled(value: float, scale: int, label: str) -> int:
    scaled = value * scale
    rounded = round(scaled)
    if not isfinite(value) or abs(scaled - rounded) > 1e-6:
        raise ExactCrossCheckError(f"{label} cannot be represented at the frozen scale")
    return rounded


def _integer_source(value: float, label: str) -> int:
    rounded = round(value)
    if not isfinite(value) or abs(value - rounded) > 1e-9:
        raise ExactCrossCheckError(f"{label} must be an integer in the frozen model")
    return rounded


def _exact_selection(value: Mapping[str, object]) -> ExactSelection:
    return ExactSelection(
        family=_string(value, "family"),
        source_instance_id=_string(value, "source_instance_id"),
        derived_instance_id=_string(value, "derived_instance_id"),
        source_sha256=_digest(value, "source_sha256"),
    )


def _required(value: Mapping[str, object], key: str) -> object:
    if key not in value:
        raise ExactCrossCheckError(f"missing protocol field: {key}")
    return value[key]


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ExactCrossCheckError(f"{label} must be an object")
    return value


def _sequence(value: object, label: str) -> Sequence[object]:
    if not isinstance(value, list):
        raise ExactCrossCheckError(f"{label} must be an array")
    return value


def _string(value: Mapping[str, object], key: str) -> str:
    item = _required(value, key)
    if not isinstance(item, str) or not item.strip():
        raise ExactCrossCheckError(f"{key} must be a non-blank string")
    return item


def _digest(value: Mapping[str, object], key: str) -> str:
    item = _string(value, key)
    if not _SHA256.fullmatch(item):
        raise ExactCrossCheckError(f"{key} must be a lowercase SHA-256")
    return item


def _integer(value: Mapping[str, object], key: str) -> int:
    item = _required(value, key)
    if not isinstance(item, int) or isinstance(item, bool):
        raise ExactCrossCheckError(f"{key} must be an integer")
    return item


def _number(value: Mapping[str, object], key: str) -> float:
    item = _required(value, key)
    if not isinstance(item, (int, float)) or isinstance(item, bool) or not isfinite(item):
        raise ExactCrossCheckError(f"{key} must be a finite number")
    return float(item)


def _boolean(value: Mapping[str, object], key: str) -> bool:
    item = _required(value, key)
    if not isinstance(item, bool):
        raise ExactCrossCheckError(f"{key} must be boolean")
    return item


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run frozen R3-315 exact cross-checks")
    subcommands = parser.add_subparsers(dest="command", required=True)
    run = subcommands.add_parser("run")
    for command in (run, subcommands.add_parser("summary")):
        command.add_argument("--protocol", type=Path, required=True)
        command.add_argument("--data-root", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
        command.add_argument("--campaign-id", required=True)
        command.add_argument("--code-revision", required=True)
    run.add_argument("--source-protocol", type=Path, required=True)
    run.add_argument("--instance", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "run":
            path = run_selected_instance(
                args.protocol,
                args.source_protocol,
                args.data_root,
                args.output,
                args.instance,
                args.campaign_id,
                args.code_revision,
            )
        else:
            path = summarize_campaign(
                args.protocol,
                args.data_root,
                args.output,
                args.campaign_id,
                args.code_revision,
            )
    except (ExactCrossCheckError, OSError, ValueError) as exc:
        print(f"R3-315 exact cross-check failed: {exc}", file=sys.stderr)
        return 2
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
