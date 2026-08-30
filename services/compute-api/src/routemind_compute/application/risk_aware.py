from __future__ import annotations

from dataclasses import dataclass

from routemind_compute.application.nearest import great_circle_distance_kilometres
from routemind_compute.domain.dispatch import CourierCandidate, DispatchDecision, DispatchProblem


@dataclass(frozen=True, slots=True)
class RiskAwareWeights:
    distance: float = 1.0
    readiness: float = 0.5
    overtime: float = 2.0
    service_risk: float = 2.0
    balance: float = 0.5

    def __post_init__(self) -> None:
        values = (self.distance, self.readiness, self.overtime, self.service_risk, self.balance)
        if any(value < 0 for value in values) or sum(values) <= 0:
            raise ValueError("risk-aware weights must be non-negative and not all zero")

    def metadata(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            (name, f"{value:.3f}")
            for name, value in (
                ("weight_distance", self.distance),
                ("weight_readiness", self.readiness),
                ("weight_overtime", self.overtime),
                ("weight_service_risk", self.service_risk),
                ("weight_balance", self.balance),
            )
        )


class RiskAwareScoringStrategy:
    name = "risk-aware"
    version = "1.0.0"
    capabilities = ("dispatch", "risk-scoring")
    maturity = "BASELINE"

    def __init__(self, weights: RiskAwareWeights | None = None) -> None:
        self.weights = weights or RiskAwareWeights()

    def _score(self, problem: DispatchProblem, candidate: CourierCandidate) -> tuple[float, ...]:
        distance = great_circle_distance_kilometres(
            problem.pickup.latitude,
            problem.pickup.longitude,
            candidate.location.latitude,
            candidate.location.longitude,
        )
        readiness_delay = max(
            0.0, candidate.available_from_seconds - problem.pickup_ready_at_seconds
        )
        balance = candidate.current_load_units / candidate.capacity_units
        components = (
            distance,
            readiness_delay / 60.0,
            candidate.overtime_risk,
            candidate.service_risk,
            balance,
        )
        return components

    def solve(self, problem: DispatchProblem) -> DispatchDecision:
        eligible = problem.eligible_candidates()
        if not eligible:
            rationale = (
                ("no eligible courier",)
                if not problem.candidates
                else ("no eligible courier", *problem.infeasibility_reasons())
            )
            return DispatchDecision(
                problem.request_id,
                self.name,
                None,
                None,
                rationale,
                self.version,
                metadata=self.weights.metadata(),
            )

        scored: list[tuple[float, str, tuple[float, ...]]] = []
        for candidate in eligible:
            components = self._score(problem, candidate)
            score = sum(
                weight * component
                for weight, component in zip(self.weights_tuple, components, strict=True)
            )
            scored.append((score, candidate.courier_id, components))
        scored.sort()
        score, courier_id, components = scored[0]
        return DispatchDecision(
            problem.request_id,
            self.name,
            courier_id,
            score,
            (
                "capacity/readiness/overtime/risk/balance weighted score",
                f"selected_components={','.join(f'{value:.3f}' for value in components)}",
            ),
            self.version,
            metadata=(*self.weights.metadata(), ("score_units", "weighted-normalized")),
        )

    @property
    def weights_tuple(self) -> tuple[float, ...]:
        return (
            self.weights.distance,
            self.weights.readiness,
            self.weights.overtime,
            self.weights.service_risk,
            self.weights.balance,
        )
