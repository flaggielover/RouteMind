from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass, field, replace
from heapq import heappop, heappush
from math import isfinite
from typing import Protocol

from opentelemetry.trace import Tracer, get_tracer

from routemind_compute.application.nearest import great_circle_distance_kilometres
from routemind_compute.domain.dispatch import GeoPoint


@dataclass(frozen=True, slots=True)
class TravelUpdate:
    """Versioned, simulated traffic and incident perturbation."""

    update_id: str
    revision: int
    effective_from_seconds: float
    traffic_multiplier: float = 1.0
    zone_multipliers: tuple[tuple[str, float], ...] = ()
    edge_delays_seconds: tuple[tuple[str, float], ...] = ()
    incident_delay_seconds: float = 0.0
    source: str = "simulated"

    def __post_init__(self) -> None:
        if not self.update_id.strip():
            raise ValueError("travel update id must not be blank")
        if (
            isinstance(self.revision, bool)
            or not isinstance(self.revision, int)
            or self.revision < 0
        ):
            raise ValueError("travel update revision must be a non-negative integer")
        if not isfinite(self.effective_from_seconds) or self.effective_from_seconds < 0:
            raise ValueError("travel update effective time must be finite and non-negative")
        if not isfinite(self.traffic_multiplier) or self.traffic_multiplier <= 0:
            raise ValueError("travel update multiplier must be finite and positive")
        if not isfinite(self.incident_delay_seconds) or self.incident_delay_seconds < 0:
            raise ValueError("travel update incident delay must be finite and non-negative")
        if not self.source.strip():
            raise ValueError("travel update source must not be blank")
        _validate_multiplier_entries(self.zone_multipliers, "zone")
        _validate_delay_entries(self.edge_delays_seconds, "edge")
        object.__setattr__(self, "zone_multipliers", tuple(sorted(self.zone_multipliers)))
        object.__setattr__(self, "edge_delays_seconds", tuple(sorted(self.edge_delays_seconds)))

    @property
    def metadata(self) -> dict[str, object]:
        return {
            "update_id": self.update_id,
            "revision": self.revision,
            "effective_from_seconds": self.effective_from_seconds,
            "traffic_multiplier": self.traffic_multiplier,
            "zone_multipliers": self.zone_multipliers,
            "edge_delays_seconds": self.edge_delays_seconds,
            "incident_delay_seconds": self.incident_delay_seconds,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class DynamicTravelContext:
    """Deterministic inputs that can change a travel estimate without I/O."""

    simulated_time_seconds: float = 0.0
    traffic_multiplier: float = 1.0
    incident_delay_seconds: float = 0.0
    traffic_context: str = "baseline"
    incident_ids: tuple[str, ...] = ()
    updates: tuple[TravelUpdate, ...] = ()

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
        update_ids = tuple(update.update_id for update in self.updates)
        if len(update_ids) != len(set(update_ids)):
            raise ValueError("travel update ids must be unique")
        object.__setattr__(self, "incident_ids", tuple(sorted(set(self.incident_ids))))
        object.__setattr__(
            self,
            "updates",
            tuple(
                sorted(
                    self.updates,
                    key=lambda update: (
                        update.effective_from_seconds,
                        update.revision,
                        update.update_id,
                    ),
                )
            ),
        )

    @property
    def metadata(self) -> dict[str, object]:
        return {
            "simulated_time_seconds": self.simulated_time_seconds,
            "traffic_multiplier": self.traffic_multiplier,
            "traffic_context": self.traffic_context,
            "incident_delay_seconds": self.incident_delay_seconds,
            "incident_ids": self.incident_ids,
            "updates": tuple(tuple(update.metadata.items()) for update in self.updates),
        }

    @property
    def replay_digest(self) -> str:
        encoded = json.dumps(self.metadata, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    def with_update(self, update: TravelUpdate) -> DynamicTravelContext:
        """Return a context with one versioned simulated update applied."""
        if any(existing.update_id == update.update_id for existing in self.updates):
            raise ValueError("travel update id must be unique")
        return replace(self, updates=(*self.updates, update))

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
    distance_kilometres: float | None = None
    traffic_seconds: float | None = None
    request_id: str | None = None
    status: str = "OK"
    error_class: str | None = None
    fallback_reason: str | None = None
    provenance: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not isfinite(self.seconds) or self.seconds < 0:
            raise ValueError("travel time seconds must be finite and non-negative")
        if not self.provider.strip():
            raise ValueError("travel provider must not be blank")
        if self.distance_kilometres is not None and (
            not isfinite(self.distance_kilometres) or self.distance_kilometres < 0
        ):
            raise ValueError("travel distance must be finite and non-negative")
        if self.traffic_seconds is not None and (
            not isfinite(self.traffic_seconds) or self.traffic_seconds < 0
        ):
            raise ValueError("traffic duration must be finite and non-negative")
        if not self.status.strip():
            raise ValueError("travel status must not be blank")
        if self.request_id is not None and not self.request_id.strip():
            raise ValueError("travel request id must not be blank")
        if any(not key.strip() or not value.strip() for key, value in self.provenance):
            raise ValueError("travel provenance entries must not be blank")
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
            "distance_kilometres": self.distance_kilometres,
            "traffic_seconds": self.traffic_seconds,
            "request_id": self.request_id,
            "status": self.status,
            "error_class": self.error_class,
            "fallback_reason": self.fallback_reason,
            "provenance": self.provenance,
            **self.context.metadata,
        }


@dataclass(frozen=True, slots=True)
class TravelTimeMatrix:
    values: tuple[tuple[TravelTime, ...], ...]
    provider: str
    context: DynamicTravelContext = field(default_factory=DynamicTravelContext)
    fallback_used: bool = False
    fallback_reason: str | None = None

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
            "fallback_reason": self.fallback_reason,
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


class TracedTravelTimeProvider:
    """Trace provider calls while preserving the provider abstraction."""

    def __init__(self, delegate: TravelTimeProvider, *, tracer: Tracer | None = None) -> None:
        self.delegate = delegate
        self.name = delegate.name
        self._tracer = tracer or get_tracer("routemind.compute.travel", "v1")

    def estimate(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        context: DynamicTravelContext | None = None,
    ) -> TravelTime:
        with self._tracer.start_as_current_span(
            "routemind.travel.estimate",
            attributes={"routemind.travel.provider": self.delegate.name},
        ) as span:
            result = _invoke_with_context(self.delegate.estimate, (origin, destination), context)
            if not isinstance(result, TravelTime):
                raise TypeError("travel provider returned an invalid point result")
            span.set_attribute("routemind.travel.result_provider", result.provider)
            span.set_attribute("routemind.travel.fallback_used", result.fallback_used)
            span.set_attribute("routemind.travel.seconds", result.seconds)
            return result

    def matrix(
        self,
        origins: Sequence[GeoPoint],
        destinations: Sequence[GeoPoint],
        context: DynamicTravelContext | None = None,
    ) -> TravelTimeMatrix:
        with self._tracer.start_as_current_span(
            "routemind.travel.matrix",
            attributes={
                "routemind.travel.provider": self.delegate.name,
                "routemind.travel.origins": len(origins),
                "routemind.travel.destinations": len(destinations),
            },
        ) as span:
            result = _invoke_with_context(self.delegate.matrix, (origins, destinations), context)
            if not isinstance(result, TravelTimeMatrix):
                raise TypeError("travel provider returned an invalid matrix result")
            span.set_attribute("routemind.travel.result_provider", result.provider)
            span.set_attribute("routemind.travel.fallback_used", result.fallback_used)
            return result


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


# Public architecture name for the deterministic local fallback. Keep the
# existing class name as a compatibility alias for callers and historical data.
LocalRoutingProvider = DeterministicLocalTravelProvider


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
            _apply_context(base_seconds, effective_context, zones=zones, edge_ids=edge_ids),
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


def _validate_multiplier_entries(entries: tuple[tuple[str, float], ...], label: str) -> None:
    keys = [key for key, _ in entries]
    if any(not key.strip() for key in keys):
        raise ValueError(f"travel update {label} keys must not be blank")
    if len(keys) != len(set(keys)):
        raise ValueError(f"travel update {label} keys must be unique")
    if any(not isfinite(value) or value <= 0 for _, value in entries):
        raise ValueError(f"travel update {label} multipliers must be finite and positive")


def _validate_delay_entries(entries: tuple[tuple[str, float], ...], label: str) -> None:
    keys = [key for key, _ in entries]
    if any(not key.strip() for key in keys):
        raise ValueError(f"travel update {label} keys must not be blank")
    if len(keys) != len(set(keys)):
        raise ValueError(f"travel update {label} keys must be unique")
    if any(not isfinite(value) or value < 0 for _, value in entries):
        raise ValueError(f"travel update {label} delays must be finite and non-negative")


def _apply_context(
    base_seconds: float,
    context: DynamicTravelContext,
    *,
    zones: tuple[str, ...] = (),
    edge_ids: tuple[str, ...] = (),
) -> float:
    multiplier = context.traffic_multiplier
    delay = context.incident_delay_seconds
    active_zones = set(zones)
    active_edges = set(edge_ids)
    for update in context.updates:
        if update.effective_from_seconds > context.simulated_time_seconds:
            continue
        multiplier *= update.traffic_multiplier
        for zone, zone_multiplier in update.zone_multipliers:
            if zone in active_zones:
                multiplier *= zone_multiplier
        delay += update.incident_delay_seconds
        delay += sum(
            edge_delay
            for edge_id, edge_delay in update.edge_delays_seconds
            if edge_id in active_edges
        )
    return base_seconds * multiplier + delay


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
        except (Exception, TimeoutError) as exc:
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
                distance_kilometres=result.distance_kilometres,
                traffic_seconds=result.traffic_seconds,
                request_id=result.request_id,
                status=result.status,
                error_class=result.error_class,
                fallback_reason=_fallback_reason(exc),
                provenance=result.provenance,
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
        except (Exception, TimeoutError) as exc:
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
                        distance_kilometres=item.distance_kilometres,
                        traffic_seconds=item.traffic_seconds,
                        request_id=item.request_id,
                        status=item.status,
                        error_class=item.error_class,
                        fallback_reason=_fallback_reason(exc),
                        provenance=item.provenance,
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
                fallback_reason=_fallback_reason(exc),
            )


def _fallback_reason(error: Exception) -> str:
    """Return a stable, non-sensitive classification for an external failure."""
    classifier = getattr(error, "classification", None)
    if isinstance(classifier, str) and classifier.strip():
        return classifier
    if isinstance(error, TimeoutError):
        return "timeout"
    return error.__class__.__name__.lower()
