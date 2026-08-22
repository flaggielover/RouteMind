from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass, field, replace
from heapq import heappop, heappush
from math import isfinite
from typing import Protocol

from routemind_compute.application.nearest import great_circle_distance_kilometres
from routemind_compute.domain.dispatch import GeoPoint


@dataclass(frozen=True, slots=True)
class DynamicTravelContext:
    """Deterministic inputs that can change a travel estimate without I/O."""

    simulated_time_seconds: float = 0.0
    traffic_multiplier: float = 1.0
    incident_delay_seconds: float = 0.0
    traffic_context: str = "baseline"
    incident_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isfinite(self.simulated_time_seconds) or self.simulated_time_seconds < 0:
            raise ValueError("simulated time must be finite and non-negative")
        if not isfinite(self.traffic_multiplier) or self.traffic_multiplier <= 0:
            raise ValueError("traffic multiplier must be finite and positive")
        if not isfinite(self.incident_delay_seconds) or self.incident_delay_seconds < 0:
            raise ValueError("incident delay must be finite and non-negative")
        if not self.traffic_context.strip():
            raise ValueError("traffic context must not be blank")
        if any(not incident_id.strip() for incident_id in self.incident_ids):
            raise ValueError("incident ids must not be blank")
        object.__setattr__(self, "incident_ids", tuple(sorted(set(self.incident_ids))))

    @property
    def metadata(self) -> dict[str, object]:
        return {
            "simulated_time_seconds": self.simulated_time_seconds,
            "traffic_multiplier": self.traffic_multiplier,
            "traffic_context": self.traffic_context,
            "incident_delay_seconds": self.incident_delay_seconds,
            "incident_ids": self.incident_ids,
        }

    def with_incident(self, incident_id: str, delay_seconds: float) -> DynamicTravelContext:
        """Return a reproducible context with one incident update applied."""
        if not incident_id.strip():
            raise ValueError("incident id must not be blank")
        if not isfinite(delay_seconds) or delay_seconds < 0:
            raise ValueError("incident delay must be finite and non-negative")
        return replace(
            self,
            incident_delay_seconds=self.incident_delay_seconds + delay_seconds,
            incident_ids=(*self.incident_ids, incident_id),
        )


@dataclass(frozen=True, slots=True)
class TravelTime:
    seconds: float
    provider: str
    fallback_used: bool = False
    context: DynamicTravelContext = field(default_factory=DynamicTravelContext)
    route_geometry: tuple[GeoPoint, ...] = ()
    edge_ids: tuple[str, ...] = ()
    zones: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isfinite(self.seconds) or self.seconds < 0:
            raise ValueError("travel time seconds must be finite and non-negative")
        if not self.provider.strip():
            raise ValueError("travel provider must not be blank")
        if any(not edge_id.strip() for edge_id in self.edge_ids):
            raise ValueError("travel edge ids must not be blank")
        if any(not zone.strip() for zone in self.zones):
            raise ValueError("travel zones must not be blank")

    @property
    def metadata(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "fallback_used": self.fallback_used,
            "route_geometry": tuple(
                (point.latitude, point.longitude) for point in self.route_geometry
            ),
            "edge_ids": self.edge_ids,
            "zones": self.zones,
            **self.context.metadata,
        }


@dataclass(frozen=True, slots=True)
class TravelTimeMatrix:
    values: tuple[tuple[TravelTime, ...], ...]
    provider: str
    context: DynamicTravelContext = field(default_factory=DynamicTravelContext)
    fallback_used: bool = False

    def __post_init__(self) -> None:
        width = len(self.values[0]) if self.values else 0
        if any(len(row) != width for row in self.values):
            raise ValueError("travel time matrix must be rectangular")
        if not self.provider.strip():
            raise ValueError("travel provider must not be blank")

    @property
    def metadata(self) -> dict[str, object]:
        width = len(self.values[0]) if self.values else 0
        return {
            "provider": self.provider,
            "fallback_used": self.fallback_used,
            "rows": len(self.values),
            "columns": width,
            **self.context.metadata,
        }


class TravelTimeProvider(Protocol):
    @property
    def name(self) -> str: ...

    def estimate(self, origin: GeoPoint, destination: GeoPoint) -> TravelTime: ...

    def matrix(
        self, origins: Sequence[GeoPoint], destinations: Sequence[GeoPoint]
    ) -> TravelTimeMatrix: ...


class DeterministicLocalTravelProvider:
    name = "deterministic-local"

    def __init__(self, speed_kilometres_per_hour: float = 30.0) -> None:
        if not isfinite(speed_kilometres_per_hour) or speed_kilometres_per_hour <= 0:
            raise ValueError("speed must be finite and positive")
        self.speed_kilometres_per_hour = speed_kilometres_per_hour

    def estimate(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        context: DynamicTravelContext | None = None,
    ) -> TravelTime:
        effective_context = context or DynamicTravelContext()
        distance = great_circle_distance_kilometres(
            origin.latitude, origin.longitude, destination.latitude, destination.longitude
        )
        base_seconds = distance / self.speed_kilometres_per_hour * 3600
        seconds = _apply_context(base_seconds, effective_context)
        return TravelTime(seconds, self.name, context=effective_context)

    def matrix(
        self,
        origins: Sequence[GeoPoint],
        destinations: Sequence[GeoPoint],
        context: DynamicTravelContext | None = None,
    ) -> TravelTimeMatrix:
        values = tuple(
            tuple(self.estimate(origin, destination, context) for destination in destinations)
            for origin in origins
        )
        effective_context = context or DynamicTravelContext()
        return TravelTimeMatrix(values, self.name, effective_context)


@dataclass(frozen=True, slots=True)
class TravelNetworkNode:
    node_id: str
    location: GeoPoint
    zone: str

    def __post_init__(self) -> None:
        if not self.node_id.strip():
            raise ValueError("network node id must not be blank")
        if not self.zone.strip():
            raise ValueError("network node zone must not be blank")


@dataclass(frozen=True, slots=True)
class TravelNetworkEdge:
    edge_id: str
    origin_node_id: str
    destination_node_id: str
    travel_seconds: float
    zone: str

    def __post_init__(self) -> None:
        if not self.edge_id.strip():
            raise ValueError("network edge id must not be blank")
        if not self.origin_node_id.strip() or not self.destination_node_id.strip():
            raise ValueError("network edge node ids must not be blank")
        if not isfinite(self.travel_seconds) or self.travel_seconds <= 0:
            raise ValueError("network edge travel seconds must be finite and positive")
        if not self.zone.strip():
            raise ValueError("network edge zone must not be blank")


@dataclass(frozen=True, slots=True)
class TravelNetworkFixture:
    nodes: tuple[TravelNetworkNode, ...]
    edges: tuple[TravelNetworkEdge, ...]

    def __post_init__(self) -> None:
        node_ids = tuple(node.node_id for node in self.nodes)
        if len(set(node_ids)) != len(node_ids):
            raise ValueError("network node ids must be unique")
        locations = tuple(node.location for node in self.nodes)
        if len(set(locations)) != len(locations):
            raise ValueError("network node locations must be unique")
        edge_ids = tuple(edge.edge_id for edge in self.edges)
        if len(set(edge_ids)) != len(edge_ids):
            raise ValueError("network edge ids must be unique")
        known_nodes = set(node_ids)
        if any(
            edge.origin_node_id not in known_nodes or edge.destination_node_id not in known_nodes
            for edge in self.edges
        ):
            raise ValueError("network edge references an unknown node")


class NetworkRouteUnavailableError(LookupError):
    """Raised when a fixture cannot route between two requested locations."""


class NetworkTravelProvider:
    """Deterministic shortest-path provider over a bounded in-memory fixture."""

    def __init__(self, fixture: TravelNetworkFixture, name: str = "network-fixture") -> None:
        if not name.strip():
            raise ValueError("network provider name must not be blank")
        self.fixture = fixture
        self.name = name
        self._nodes_by_location = {node.location: node for node in fixture.nodes}
        self._nodes_by_id = {node.node_id: node for node in fixture.nodes}
        self._outgoing: dict[str, tuple[TravelNetworkEdge, ...]] = {
            node.node_id: tuple(
                sorted(
                    (edge for edge in fixture.edges if edge.origin_node_id == node.node_id),
                    key=lambda edge: edge.edge_id,
                )
            )
            for node in fixture.nodes
        }

    @property
    def metadata(self) -> dict[str, object]:
        return {
            "provider": self.name,
            "node_count": len(self.fixture.nodes),
            "edge_count": len(self.fixture.edges),
        }

    def _route(
        self, origin: GeoPoint, destination: GeoPoint
    ) -> tuple[float, tuple[GeoPoint, ...], tuple[str, ...], tuple[str, ...]]:
        origin_node = self._nodes_by_location.get(origin)
        destination_node = self._nodes_by_location.get(destination)
        if origin_node is None or destination_node is None:
            raise NetworkRouteUnavailableError("network fixture does not contain both locations")
        if origin_node.node_id == destination_node.node_id:
            return 0.0, (origin,), (), (origin_node.zone,)

        queue: list[tuple[float, tuple[str, ...], str, tuple[str, ...], tuple[str, ...]]] = []
        heappush(queue, (0.0, (), origin_node.node_id, (origin_node.node_id,), ()))
        best: dict[str, tuple[float, tuple[str, ...]]] = {}
        while queue:
            total_seconds, path_edges, node_id, path_nodes, path_zones = heappop(queue)
            score = (total_seconds, path_edges)
            previous = best.get(node_id)
            if previous is not None and previous <= score:
                continue
            best[node_id] = score
            if node_id == destination_node.node_id:
                geometry = tuple(self._nodes_by_id[item].location for item in path_nodes)
                return total_seconds, geometry, path_edges, path_zones
            for edge in self._outgoing[node_id]:
                heappush(
                    queue,
                    (
                        total_seconds + edge.travel_seconds,
                        (*path_edges, edge.edge_id),
                        edge.destination_node_id,
                        (*path_nodes, edge.destination_node_id),
                        (*path_zones, edge.zone),
                    ),
                )
        raise NetworkRouteUnavailableError(
            f"network fixture has no route from {origin_node.node_id} to {destination_node.node_id}"
        )

    def estimate(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        context: DynamicTravelContext | None = None,
    ) -> TravelTime:
        effective_context = context or DynamicTravelContext()
        base_seconds, geometry, edge_ids, zones = self._route(origin, destination)
        return TravelTime(
            _apply_context(base_seconds, effective_context),
            self.name,
            context=effective_context,
            route_geometry=geometry,
            edge_ids=edge_ids,
            zones=zones,
        )

    def matrix(
        self,
        origins: Sequence[GeoPoint],
        destinations: Sequence[GeoPoint],
        context: DynamicTravelContext | None = None,
    ) -> TravelTimeMatrix:
        effective_context = context or DynamicTravelContext()
        values = tuple(
            tuple(
                self.estimate(origin, destination, effective_context)
                for destination in destinations
            )
            for origin in origins
        )
        return TravelTimeMatrix(values, self.name, effective_context)


def _apply_context(base_seconds: float, context: DynamicTravelContext) -> float:
    return base_seconds * context.traffic_multiplier + context.incident_delay_seconds


def _invoke_with_context(
    operation: Callable[..., TravelTime | TravelTimeMatrix],
    args: tuple[object, ...],
    context: DynamicTravelContext | None,
) -> TravelTime | TravelTimeMatrix:
    if context is None:
        return operation(*args)
    try:
        return operation(*args, context=context)
    except TypeError:
        # Keep older provider implementations usable while they migrate.
        return operation(*args)


class FallbackTravelTimeProvider:
    def __init__(
        self,
        primary: TravelTimeProvider,
        fallback: TravelTimeProvider,
        timeout_seconds: float = 1.0,
    ) -> None:
        if timeout_seconds <= 0 or not isfinite(timeout_seconds):
            raise ValueError("timeout must be finite and positive")
        self.primary = primary
        self.fallback = fallback
        self.timeout_seconds = timeout_seconds
        self.name = f"fallback({primary.name}->{fallback.name})"

    def _call_with_timeout(
        self,
        operation: Callable[..., TravelTime | TravelTimeMatrix],
        *args: object,
        context: DynamicTravelContext | None = None,
    ) -> TravelTime | TravelTimeMatrix:
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(_invoke_with_context, operation, args, context)
            return future.result(timeout=self.timeout_seconds)
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def estimate(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        context: DynamicTravelContext | None = None,
    ) -> TravelTime:
        try:
            result = self._call_with_timeout(
                self.primary.estimate, origin, destination, context=context
            )
            if not isinstance(result, TravelTime):
                raise TypeError("primary provider returned an invalid point result")
            return result
        except (Exception, TimeoutError):
            result = _invoke_with_context(self.fallback.estimate, (origin, destination), context)
            if not isinstance(result, TravelTime):
                raise TypeError("fallback provider returned an invalid point result") from None
            return TravelTime(
                result.seconds,
                result.provider,
                fallback_used=True,
                context=result.context,
                route_geometry=result.route_geometry,
                edge_ids=result.edge_ids,
                zones=result.zones,
            )

    def matrix(
        self,
        origins: Sequence[GeoPoint],
        destinations: Sequence[GeoPoint],
        context: DynamicTravelContext | None = None,
    ) -> TravelTimeMatrix:
        try:
            result = self._call_with_timeout(
                self.primary.matrix, origins, destinations, context=context
            )
            if not isinstance(result, TravelTimeMatrix):
                raise TypeError("primary provider returned an invalid matrix result")
            return result
        except (Exception, TimeoutError):
            raw_result = _invoke_with_context(
                self.fallback.matrix, (origins, destinations), context
            )
            if not isinstance(raw_result, TravelTimeMatrix):
                raise TypeError("fallback provider returned an invalid matrix result") from None
            result = raw_result
            values = tuple(
                tuple(
                    TravelTime(
                        item.seconds,
                        item.provider,
                        fallback_used=True,
                        context=item.context,
                        route_geometry=item.route_geometry,
                        edge_ids=item.edge_ids,
                        zones=item.zones,
                    )
                    for item in row
                )
                for row in result.values
            )
            return TravelTimeMatrix(
                values,
                result.provider,
                result.context,
                fallback_used=True,
            )
