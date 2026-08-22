from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Protocol

from routemind_compute.application.travel import DeterministicLocalTravelProvider, TravelTime
from routemind_compute.domain.dispatch import (
    DispatchDecision,
    DispatchProblem,
    GeoPoint,
    TimeWindow,
)

MAX_VRP_STOPS = 32
MAX_VRP_VEHICLES = 32


class RouteTravelProvider(Protocol):
    def estimate(self, origin: GeoPoint, destination: GeoPoint) -> TravelTime: ...


@dataclass(frozen=True, slots=True)
class VrpStop:
    stop_id: str
    location: GeoPoint
    demand_units: float = 1.0
    service_seconds: float = 0.0
    time_window: TimeWindow | None = None

    def __post_init__(self) -> None:
        if not self.stop_id.strip():
            raise ValueError("stop_id must not be blank")
        if not isfinite(self.demand_units) or self.demand_units <= 0:
            raise ValueError("stop demand must be finite and positive")
        if not isfinite(self.service_seconds) or self.service_seconds < 0:
            raise ValueError("stop service seconds must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class VrpVehicle:
    vehicle_id: str
    start_location: GeoPoint
    capacity_units: float
    available_from_seconds: float = 0.0
    available_until_seconds: float | None = None

    def __post_init__(self) -> None:
        if not self.vehicle_id.strip():
            raise ValueError("vehicle_id must not be blank")
        if not isfinite(self.capacity_units) or self.capacity_units < 0:
            raise ValueError("vehicle capacity must be finite and non-negative")
        if not isfinite(self.available_from_seconds) or self.available_from_seconds < 0:
            raise ValueError("vehicle availability must be finite and non-negative")
        if self.available_until_seconds is not None and (
            not isfinite(self.available_until_seconds)
            or self.available_until_seconds < self.available_from_seconds
        ):
            raise ValueError("vehicle availability window must be ordered and finite")


@dataclass(frozen=True, slots=True)
class VrpProblem:
    problem_id: str
    depot: GeoPoint
    stops: tuple[VrpStop, ...]
    vehicles: tuple[VrpVehicle, ...]
    return_to_depot: bool = True

    def __post_init__(self) -> None:
        if not self.problem_id.strip():
            raise ValueError("problem_id must not be blank")
        if len(self.stops) > MAX_VRP_STOPS:
            raise ValueError(f"VRP stop count must not exceed {MAX_VRP_STOPS}")
        if len(self.vehicles) > MAX_VRP_VEHICLES:
            raise ValueError(f"VRP vehicle count must not exceed {MAX_VRP_VEHICLES}")
        stop_ids = tuple(stop.stop_id for stop in self.stops)
        if len(stop_ids) != len(set(stop_ids)):
            raise ValueError("stop identifiers must be unique")
        vehicle_ids = tuple(vehicle.vehicle_id for vehicle in self.vehicles)
        if len(vehicle_ids) != len(set(vehicle_ids)):
            raise ValueError("vehicle identifiers must be unique")


@dataclass(frozen=True, slots=True)
class VrpRoute:
    vehicle_id: str
    stop_ids: tuple[str, ...]
    arrival_seconds: tuple[float, ...]
    service_start_seconds: tuple[float, ...]
    departure_seconds: tuple[float, ...]
    load_units: float
    travel_seconds: float
    completion_seconds: float


@dataclass(frozen=True, slots=True)
class VrpRoutePlan:
    problem_id: str
    routes: tuple[VrpRoute, ...]
    unassigned: tuple[tuple[str, str], ...]
    total_travel_seconds: float
    strategy: str = "greedy-vrptw"
    strategy_version: str = "1.0.0"


@dataclass(frozen=True, slots=True)
class VrpInsertionDecision:
    accepted: bool
    route: VrpRoute | None
    insertion_position: int | None
    incremental_travel_seconds: float | None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class _RouteEvaluation:
    feasible: bool
    route: VrpRoute | None
    reason: str | None = None


def _travel_seconds(
    provider: RouteTravelProvider, origin: GeoPoint, destination: GeoPoint
) -> float:
    result = provider.estimate(origin, destination)
    seconds = getattr(result, "seconds", None)
    if not isinstance(seconds, (int, float)) or isinstance(seconds, bool) or not isfinite(seconds):
        raise ValueError("travel provider returned invalid seconds")
    if seconds < 0:
        raise ValueError("travel provider returned negative seconds")
    return float(seconds)


class VrptwRoutePlanner:
    """Bounded deterministic insertion baseline for small VRP/VRPTW instances."""

    name = "greedy-vrptw"
    version = "1.0.0"

    def __init__(self, travel_provider: RouteTravelProvider | None = None) -> None:
        self.travel_provider = travel_provider or DeterministicLocalTravelProvider()

    def plan(self, problem: VrpProblem) -> VrpRoutePlan:
        stop_by_id = {stop.stop_id: stop for stop in problem.stops}
        route_ids_by_vehicle: dict[str, tuple[str, ...]] = {
            vehicle.vehicle_id: () for vehicle in problem.vehicles
        }
        evaluations: dict[str, _RouteEvaluation] = {}
        unassigned: list[tuple[str, str]] = []
        ordered_stops = sorted(
            problem.stops,
            key=lambda stop: (
                stop.time_window.start_seconds if stop.time_window is not None else 0.0,
                stop.stop_id,
            ),
        )

        for stop in ordered_stops:
            options: list[
                tuple[
                    tuple[float, tuple[str, ...], str, int],
                    str,
                    tuple[str, ...],
                    _RouteEvaluation,
                ]
            ] = []
            reasons: set[str] = set()
            for vehicle in problem.vehicles:
                current_ids = route_ids_by_vehicle[vehicle.vehicle_id]
                current = evaluations.get(vehicle.vehicle_id)
                current_cost = current.route.travel_seconds if current and current.route else 0.0
                for position in range(len(current_ids) + 1):
                    candidate_ids = (*current_ids[:position], stop.stop_id, *current_ids[position:])
                    evaluation = self._evaluate(vehicle, candidate_ids, stop_by_id, problem)
                    if evaluation.feasible and evaluation.route is not None:
                        key = (
                            evaluation.route.travel_seconds - current_cost,
                            candidate_ids,
                            vehicle.vehicle_id,
                            position,
                        )
                        options.append((key, vehicle.vehicle_id, candidate_ids, evaluation))
                    elif evaluation.reason is not None:
                        reasons.add(evaluation.reason)
            if not options:
                reason = sorted(reasons)[0] if reasons else "no feasible route"
                unassigned.append((stop.stop_id, reason))
                continue
            _, vehicle_id, stop_ids, evaluation = min(options, key=lambda item: item[0])
            route_ids_by_vehicle[vehicle_id] = stop_ids
            evaluations[vehicle_id] = evaluation

        final_routes = tuple(
            evaluations[vehicle_id].route
            for vehicle_id in sorted(evaluations)
            if evaluations[vehicle_id].route is not None
        )
        route_records = tuple(route for route in final_routes if route is not None)
        return VrpRoutePlan(
            problem_id=problem.problem_id,
            routes=route_records,
            unassigned=tuple(sorted(unassigned)),
            total_travel_seconds=sum(route.travel_seconds for route in route_records),
            strategy=self.name,
            strategy_version=self.version,
        )

    def insert(
        self,
        problem: VrpProblem,
        active_route: VrpRoute,
        stop: VrpStop,
    ) -> VrpInsertionDecision:
        """Return a new route with one stop inserted, without mutating the snapshot."""
        if len(problem.stops) >= MAX_VRP_STOPS:
            return VrpInsertionDecision(False, None, None, None, "stop_limit_exceeded")
        if stop.stop_id in {item.stop_id for item in problem.stops}:
            return VrpInsertionDecision(False, None, None, None, "stop_id_conflict")
        vehicle = next(
            (item for item in problem.vehicles if item.vehicle_id == active_route.vehicle_id),
            None,
        )
        if vehicle is None:
            return VrpInsertionDecision(False, None, None, None, "vehicle_not_found")
        stop_by_id = {item.stop_id: item for item in problem.stops}
        if any(stop_id not in stop_by_id for stop_id in active_route.stop_ids):
            return VrpInsertionDecision(False, None, None, None, "route_stop_not_found")
        current = self._evaluate(vehicle, active_route.stop_ids, stop_by_id, problem)
        if not current.feasible or current.route is None:
            return VrpInsertionDecision(False, None, None, None, "active_route_infeasible")
        stop_by_id[stop.stop_id] = stop
        options: list[tuple[tuple[float, tuple[str, ...], int], int, _RouteEvaluation]] = []
        reasons: set[str] = set()
        for position in range(len(active_route.stop_ids) + 1):
            candidate_ids = (
                *active_route.stop_ids[:position],
                stop.stop_id,
                *active_route.stop_ids[position:],
            )
            evaluation = self._evaluate(vehicle, candidate_ids, stop_by_id, problem)
            if evaluation.feasible and evaluation.route is not None:
                key = (
                    evaluation.route.travel_seconds - current.route.travel_seconds,
                    candidate_ids,
                    position,
                )
                options.append((key, position, evaluation))
            elif evaluation.reason is not None:
                reasons.add(evaluation.reason)
        if not options:
            reason = sorted(reasons)[0] if reasons else "no feasible insertion"
            return VrpInsertionDecision(False, None, None, None, reason)
        _, position, evaluation = min(options, key=lambda item: item[0])
        assert evaluation.route is not None
        return VrpInsertionDecision(
            True,
            evaluation.route,
            position,
            evaluation.route.travel_seconds - current.route.travel_seconds,
        )

    def _evaluate(
        self,
        vehicle: VrpVehicle,
        stop_ids: tuple[str, ...],
        stop_by_id: dict[str, VrpStop],
        problem: VrpProblem,
    ) -> _RouteEvaluation:
        current = vehicle.start_location
        clock = vehicle.available_from_seconds
        load = 0.0
        travel = 0.0
        arrivals: list[float] = []
        service_starts: list[float] = []
        departures: list[float] = []
        for stop_id in stop_ids:
            stop = stop_by_id[stop_id]
            load += stop.demand_units
            if load > vehicle.capacity_units + 1e-9:
                return _RouteEvaluation(False, None, "capacity_insufficient")
            leg = _travel_seconds(self.travel_provider, current, stop.location)
            travel += leg
            arrival = clock + leg
            service_start = max(
                arrival, stop.time_window.start_seconds if stop.time_window else 0.0
            )
            if stop.time_window is not None and service_start > stop.time_window.end_seconds + 1e-9:
                return _RouteEvaluation(False, None, "time_window_missed")
            departure = service_start + stop.service_seconds
            if (
                vehicle.available_until_seconds is not None
                and departure > vehicle.available_until_seconds + 1e-9
            ):
                return _RouteEvaluation(False, None, "vehicle_unavailable_until")
            arrivals.append(arrival)
            service_starts.append(service_start)
            departures.append(departure)
            current = stop.location
            clock = departure
        if problem.return_to_depot and stop_ids:
            return_leg = _travel_seconds(self.travel_provider, current, problem.depot)
            travel += return_leg
            clock += return_leg
            if (
                vehicle.available_until_seconds is not None
                and clock > vehicle.available_until_seconds + 1e-9
            ):
                return _RouteEvaluation(False, None, "vehicle_unavailable_until")
        route = VrpRoute(
            vehicle_id=vehicle.vehicle_id,
            stop_ids=stop_ids,
            arrival_seconds=tuple(arrivals),
            service_start_seconds=tuple(service_starts),
            departure_seconds=tuple(departures),
            load_units=load,
            travel_seconds=travel,
            completion_seconds=clock,
        )
        return _RouteEvaluation(True, route)


class VrptwStrategy:
    name = "vrptw"
    version = "1.0.0"
    capabilities = ("dispatch", "vrp", "vrptw")

    def __init__(self, planner: VrptwRoutePlanner | None = None) -> None:
        self.planner = planner or VrptwRoutePlanner()

    def solve(self, problem: DispatchProblem) -> DispatchDecision:
        eligible = problem.eligible_candidates()
        if not eligible:
            return DispatchDecision(
                problem.request_id,
                self.name,
                None,
                None,
                ("no feasible VRPTW route", *problem.infeasibility_reasons()),
                self.version,
            )
        route_problem = VrpProblem(
            problem.request_id,
            problem.pickup,
            (
                VrpStop(
                    problem.request_id,
                    problem.pickup,
                    demand_units=problem.demand_units,
                    service_seconds=problem.service_seconds,
                    time_window=problem.delivery_window,
                ),
            ),
            tuple(
                VrpVehicle(
                    candidate.courier_id,
                    candidate.location,
                    candidate.capacity_units - candidate.current_load_units,
                    candidate.available_from_seconds,
                    candidate.available_until_seconds,
                )
                for candidate in eligible
            ),
            return_to_depot=False,
        )
        plan = self.planner.plan(route_problem)
        if plan.unassigned or not plan.routes:
            reasons = tuple(f"{request_id}:{reason}" for request_id, reason in plan.unassigned)
            return DispatchDecision(
                problem.request_id,
                self.name,
                None,
                None,
                ("no feasible VRPTW route", *reasons),
                self.version,
            )
        route = plan.routes[0]
        return DispatchDecision(
            problem.request_id,
            self.name,
            route.vehicle_id,
            route.travel_seconds,
            ("lowest feasible VRPTW route",),
            self.version,
            metadata=(
                ("route_stop_count", str(len(route.stop_ids))),
                ("route_travel_seconds", f"{route.travel_seconds:.3f}"),
                ("route_completion_seconds", f"{route.completion_seconds:.3f}"),
                ("route_return_to_depot", "false"),
            ),
        )
