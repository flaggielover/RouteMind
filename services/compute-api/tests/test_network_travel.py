from __future__ import annotations

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
    with pytest.raises(ValueError, match="node zone"):
        TravelNetworkNode("a", A, " ")
    with pytest.raises(ValueError, match="edge travel"):
        TravelNetworkEdge("e", "a", "b", 0, "north")
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
    with pytest.raises(ValueError, match="name"):
        NetworkTravelProvider(network_provider().fixture, " ")
