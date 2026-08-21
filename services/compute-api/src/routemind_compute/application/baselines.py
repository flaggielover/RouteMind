from __future__ import annotations

from math import isfinite

from routemind_compute.application.nearest import great_circle_distance_kilometres
from routemind_compute.domain.dispatch import DispatchDecision, DispatchProblem


def _ranked_candidates(problem: DispatchProblem, weight: float) -> list[tuple[float, str]]:
    if weight <= 0 or not isfinite(weight):
        raise ValueError("distance weight must be finite and positive")
    return sorted(
        (
            weight
            * great_circle_distance_kilometres(
                problem.pickup.latitude,
                problem.pickup.longitude,
                candidate.location.latitude,
                candidate.location.longitude,
            ),
            candidate.courier_id,
        )
        for candidate in problem.candidates
    )


class WeightedGreedyStrategy:
    name = "weighted-greedy"
    version = "1.0.0"

    def __init__(self, distance_weight: float = 1.0) -> None:
        self.distance_weight = distance_weight

    def solve(self, problem: DispatchProblem) -> DispatchDecision:
        ranked = _ranked_candidates(problem, self.distance_weight)
        if not ranked:
            return DispatchDecision(
                problem.request_id,
                self.name,
                None,
                None,
                ("no eligible courier",),
                self.version,
            )
        score, courier_id = ranked[0]
        return DispatchDecision(
            problem.request_id,
            self.name,
            courier_id,
            score,
            ("lowest weighted pickup distance",),
            self.version,
        )


class HungarianStrategy:
    name = "hungarian"
    version = "1.0.0"

    @staticmethod
    def assign(costs: tuple[tuple[float, ...], ...]) -> tuple[tuple[int, int], ...]:
        """Return minimum-cost row/column pairs for a rectangular cost matrix."""
        if not costs or not costs[0]:
            return ()
        width = len(costs[0])
        if any(len(row) != width for row in costs):
            raise ValueError("cost matrix must be rectangular")
        if any(not isfinite(value) for row in costs for value in row):
            raise ValueError("cost matrix must contain finite values")

        rows = len(costs)
        if rows > width:
            transposed = tuple(
                tuple(costs[row][column] for row in range(rows)) for column in range(width)
            )
            return tuple(
                sorted((column, row) for row, column in HungarianStrategy.assign(transposed))
            )

        # Potentials-based Hungarian algorithm for rows <= columns.
        u = [0.0] * (rows + 1)
        v = [0.0] * (width + 1)
        matching = [0] * (width + 1)
        for row in range(1, rows + 1):
            matching[0] = row
            column = 0
            minimum = [float("inf")] * (width + 1)
            visited = [False] * (width + 1)
            previous = [0] * (width + 1)
            while True:
                visited[column] = True
                active_row = matching[column]
                delta = float("inf")
                next_column = 0
                for candidate in range(1, width + 1):
                    if visited[candidate]:
                        continue
                    reduced = costs[active_row - 1][candidate - 1] - u[active_row] - v[candidate]
                    if reduced < minimum[candidate]:
                        minimum[candidate] = reduced
                        previous[candidate] = column
                    if minimum[candidate] < delta:
                        delta = minimum[candidate]
                        next_column = candidate
                for candidate in range(width + 1):
                    if visited[candidate]:
                        u[matching[candidate]] += delta
                        v[candidate] -= delta
                    else:
                        minimum[candidate] -= delta
                column = next_column
                if matching[column] == 0:
                    break
            while True:
                prior = previous[column]
                matching[column] = matching[prior]
                column = prior
                if column == 0:
                    break
        return tuple(
            sorted(
                (matching[column] - 1, column - 1)
                for column in range(1, width + 1)
                if matching[column]
            )
        )

    def solve(self, problem: DispatchProblem) -> DispatchDecision:
        ranked = _ranked_candidates(problem, 1.0)
        if not ranked:
            return DispatchDecision(
                problem.request_id,
                self.name,
                None,
                None,
                ("no eligible courier",),
                self.version,
            )
        score, courier_id = ranked[0]
        return DispatchDecision(
            problem.request_id,
            self.name,
            courier_id,
            score,
            ("minimum-cost assignment for one request",),
            self.version,
        )
