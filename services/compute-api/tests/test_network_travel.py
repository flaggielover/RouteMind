from __future__ import annotations

from typing import cast

import pytest

from routemind_compute.application.travel import (
    DeterministicLocalTravelProvider,
    DynamicTravelContext,
    FallbackTravelTimeProvider,
    NetworkRouteUnavailableError,
    NetworkTravelProvider,
    TravelNetworkEdge,
    TravelNetworkFixture,
    TravelNetworkNode,
    TravelTime,
    TravelUpdate,
)
from routemind_compute.domain.dispatch import GeoPoint

A = GeoPoint(31.0, 121.0)
B = GeoPoint(31.001, 121.0)
C = GeoPoint(31.002, 121.0)
D = GeoPoint(31.001, 121.001)
E = GeoPoint(31.003, 121.0)


def network_provider() -> NetworkTravelProvider:
    fixture = TravelNetworkFixture(
        nodes=(
            TravelNetworkNode("a", A, "north"),
            TravelNetworkNode("b", B, "north"),
            TravelNetworkNode("c", C, "north"),
            TravelNetworkNode("d", D, "south"),
            TravelNetworkNode("e", E, "south"),
        ),
        edges=(
            TravelNetworkEdge("e-ab", "a", "b", 5, "north-edge"),
            TravelNetworkEdge("e-bc", "b", "c", 5, "north-edge"),
            TravelNetworkEdge("e-ad", "a", "d", 2, "south-edge"),
            TravelNetworkEdge("e-dc", "d", "c", 8, "south-edge"),
        ),
    )
    return NetworkTravelProvider(fixture)


def test_network_provider_returns_deterministic_geometry_and_edge_metadata() -> None:
    provider = network_provider()
    context = DynamicTravelContext(traffic_multiplier=1.2, incident_delay_seconds=3)

    result = provider.estimate(A, C, context)
    matrix = provider.matrix((A, D), (C,), context)

    assert result.seconds == pytest.approx(15)
    assert result.route_geometry == (A, B, C)
    assert result.edge_ids == ("e-ab", "e-bc")
    assert result.zones == ("north-edge", "north-edge")
    assert result.context == context
    assert result.metadata["provider"] == "network-fixture"
    assert matrix.values[0][0].edge_ids == result.edge_ids
    assert matrix.values[1][0].edge_ids == ("e-dc",)
    assert matrix.metadata["rows"] == 2


def test_versioned_updates_apply_by_simulated_time_zone_and_edge() -> None:
    provider = network_provider()
    update = TravelUpdate(
        "rush-hour-incident",
        revision=2,
        effective_from_seconds=3600,
        traffic_multiplier=1.1,
        zone_multipliers=(("north-edge", 1.5),),
        edge_delays_seconds=(("e-bc", 20),),
        incident_delay_seconds=5,
    )
    before = DynamicTravelContext(simulated_time_seconds=3599).with_update(update)
    active = DynamicTravelContext(simulated_time_seconds=3600).with_update(update)

    assert provider.estimate(A, C, before).seconds == 10
    result = provider.estimate(A, C, active)
    assert result.seconds == pytest.approx(41.5)
    assert result.context.replay_digest == active.replay_digest
    updates = cast(tuple[tuple[tuple[str, object], ...], ...], active.metadata["updates"])
    assert updates[0][0][0] == "update_id"
    assert updates[0][1][1] == 2


def test_updates_are_versioned_and_validated() -> None:
    with pytest.raises(ValueError, match="update id"):
        TravelUpdate("", 1, 0)
    with pytest.raises(ValueError, match="effective time"):
        TravelUpdate("update", 1, -1)
    with pytest.raises(ValueError, match="multiplier"):
        TravelUpdate("update", 1, 0, traffic_multiplier=0)
    with pytest.raises(ValueError, match="incident delay"):
        TravelUpdate("update", 1, 0, incident_delay_seconds=-1)
    with pytest.raises(ValueError, match="source"):
        TravelUpdate("update", 1, 0, source=" ")
    with pytest.raises(ValueError, match="revision"):
        TravelUpdate("update", -1, 0)
    with pytest.raises(ValueError, match="zone keys"):
        TravelUpdate("update", 1, 0, zone_multipliers=(("", 1),))
    with pytest.raises(ValueError, match="zone keys"):
        TravelUpdate("update", 1, 0, zone_multipliers=(("north", 1), ("north", 1)))
    with pytest.raises(ValueError, match="zone multipliers"):
        TravelUpdate("update", 1, 0, zone_multipliers=(("north", 0),))
    with pytest.raises(ValueError, match="edge keys"):
        TravelUpdate("update", 1, 0, edge_delays_seconds=(("", 1),))
    with pytest.raises(ValueError, match="edge keys"):
        TravelUpdate("update", 1, 0, edge_delays_seconds=(("edge", 1), ("edge", 2)))
    with pytest.raises(ValueError, match="edge delays"):
        TravelUpdate("update", 1, 0, edge_delays_seconds=(("edge", -1),))
    update = TravelUpdate("update", 1, 0)
    with pytest.raises(ValueError, match="unique"):
        DynamicTravelContext().with_update(update).with_update(update)
    with pytest.raises(ValueError, match="unique"):
        DynamicTravelContext(updates=(update, update))


def test_travel_result_and_context_reject_invalid_values() -> None:
    with pytest.raises(ValueError, match="simulated time"):
        DynamicTravelContext(simulated_time_seconds=-1)
    with pytest.raises(ValueError, match="incident delay"):
        DynamicTravelContext(incident_delay_seconds=-1)
    with pytest.raises(ValueError, match="edge ids"):
        TravelTime(1, "test", edge_ids=("",))
    with pytest.raises(ValueError, match="zones"):
        TravelTime(1, "test", zones=("",))


def test_network_provider_handles_same_node_and_unavailable_routes() -> None:
    provider = network_provider()

    same = provider.estimate(A, A)
    assert same.seconds == 0
    assert same.route_geometry == (A,)
    assert same.zones == ("north",)

    with pytest.raises(NetworkRouteUnavailableError, match="no route"):
        provider.estimate(A, E)
    with pytest.raises(NetworkRouteUnavailableError, match="both locations"):
        provider.estimate(A, GeoPoint(31.1, 121.1))


def test_network_provider_is_replaceable_and_fallback_is_explicit() -> None:
    provider = FallbackTravelTimeProvider(
        network_provider(), DeterministicLocalTravelProvider(), timeout_seconds=0.1
    )
    context = DynamicTravelContext(traffic_context="replay")

    result = provider.estimate(A, E, context)

    assert result.fallback_used
    assert result.provider == "deterministic-local"
    assert result.context == context
    assert result.route_geometry == ()


def test_network_fixture_rejects_invalid_topology() -> None:
    with pytest.raises(ValueError, match="node id"):
        TravelNetworkNode(" ", A, "north")
    with pytest.raises(ValueError, match="node zone"):
        TravelNetworkNode("a", A, " ")
    with pytest.raises(ValueError, match="edge travel"):
        TravelNetworkEdge("e", "a", "b", 0, "north")
    with pytest.raises(ValueError, match="edge id"):
        TravelNetworkEdge(" ", "a", "b", 1, "north")
    with pytest.raises(ValueError, match="node ids"):
        TravelNetworkEdge("e", " ", "b", 1, "north")
    with pytest.raises(ValueError, match="edge zone"):
        TravelNetworkEdge("e", "a", "b", 1, " ")
    with pytest.raises(ValueError, match="unknown node"):
        TravelNetworkFixture(
            (TravelNetworkNode("a", A, "north"),),
            (TravelNetworkEdge("e", "a", "missing", 1, "north"),),
        )
    with pytest.raises(ValueError, match="unique"):
        TravelNetworkFixture(
            (TravelNetworkNode("a", A, "north"), TravelNetworkNode("a", B, "north")),
            (),
        )
    with pytest.raises(ValueError, match="locations"):
        TravelNetworkFixture(
            (TravelNetworkNode("a", A, "north"), TravelNetworkNode("b", A, "north")),
            (),
        )
    with pytest.raises(ValueError, match="edge ids"):
        TravelNetworkFixture(
            (TravelNetworkNode("a", A, "north"), TravelNetworkNode("b", B, "north")),
            (
                TravelNetworkEdge("e", "a", "b", 1, "north"),
                TravelNetworkEdge("e", "b", "a", 1, "north"),
            ),
        )
    with pytest.raises(ValueError, match="name"):
        NetworkTravelProvider(network_provider().fixture, " ")


def test_fallback_provider_preserves_primary_matrix_and_rejects_invalid_fallback() -> None:
    primary = network_provider()
    fallback = FallbackTravelTimeProvider(primary, DeterministicLocalTravelProvider())
    matrix = fallback.matrix((A,), (C,))
    assert matrix.fallback_used is False
    assert matrix.values[0][0].edge_ids == ("e-ab", "e-bc")

    class InvalidFallback:
        name = "invalid-fallback"

        def estimate(self, origin: GeoPoint, destination: GeoPoint) -> object:
            return "invalid"

        def matrix(
            self, origins: tuple[GeoPoint, ...], destinations: tuple[GeoPoint, ...]
        ) -> object:
            return "invalid"

    invalid = FallbackTravelTimeProvider(primary, InvalidFallback())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="fallback provider"):
        invalid.estimate(A, E)
    with pytest.raises(TypeError, match="fallback provider"):
        invalid.matrix((A,), (E,))
