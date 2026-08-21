from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from routemind_compute.domain.dispatch import DispatchDecision, DispatchProblem

EARTH_RADIUS_KILOMETRES = 6371.0088


def great_circle_distance_kilometres(
    latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float
) -> float:
    """Return the Haversine distance between two validated geographic points."""
    latitude_delta = radians(latitude_b - latitude_a)
    longitude_delta = radians(longitude_b - longitude_a)
    first = sin(latitude_delta / 2) ** 2
    second = cos(radians(latitude_a)) * cos(radians(latitude_b)) * sin(longitude_delta / 2) ** 2
    return 2 * EARTH_RADIUS_KILOMETRES * asin(sqrt(first + second))


class NearestStrategy:
    name = "nearest"
    version = "1.0.0"

    def solve(self, problem: DispatchProblem) -> DispatchDecision:
        if not problem.candidates:
            return DispatchDecision(
                request_id=problem.request_id,
                strategy=self.name,
                courier_id=None,
                score=None,
                rationale=("no eligible courier",),
                strategy_version=self.version,
            )

        ranked = sorted(
            (
                great_circle_distance_kilometres(
                    problem.pickup.latitude,
                    problem.pickup.longitude,
                    candidate.location.latitude,
                    candidate.location.longitude,
                ),
                candidate.courier_id,
            )
            for candidate in problem.candidates
        )
        distance, courier_id = ranked[0]
        return DispatchDecision(
            request_id=problem.request_id,
            strategy=self.name,
            courier_id=courier_id,
            score=distance,
            rationale=("lowest great-circle distance",),
            strategy_version=self.version,
        )
