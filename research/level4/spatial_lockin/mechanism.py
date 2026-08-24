from __future__ import annotations

import random
from dataclasses import dataclass
from math import atan, exp, pi, tanh

from .reason_codes import fail

MechanismVector = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class ZonePopulation:
    couriers: float
    merchant_capacity: float
    latent_demand: float


@dataclass(frozen=True, slots=True)
class MechanismState:
    region_a: ZonePopulation
    region_b: ZonePopulation


@dataclass(frozen=True, slots=True)
class OperationalMetrics:
    accepted_a: float
    accepted_b: float
    served_a: float
    served_b: float
    wait_a: float
    wait_b: float
    utilization_a: float
    utilization_b: float
    courier_opportunity_a: float
    courier_opportunity_b: float
    service_inequality: float


@dataclass(frozen=True, slots=True)
class MechanismRun:
    seed: int
    alpha: float
    states: tuple[MechanismState, ...]
    observations: tuple[MechanismVector, ...]
    metrics: tuple[OperationalMetrics, ...]


@dataclass(frozen=True, slots=True)
class DeliveryMechanism:
    parameters: dict[str, object]

    @classmethod
    def from_config(cls, payload: dict[str, object]) -> DeliveryMechanism:
        required = {
            "model_version",
            "baseline_couriers",
            "baseline_merchant_capacity",
            "baseline_demand",
            "base_acceptance",
            "courier_persistence",
            "merchant_persistence",
            "demand_persistence",
            "courier_response",
            "merchant_response",
            "customer_response",
            "supply_acceptance_weight",
            "merchant_acceptance_weight",
            "dispatch_priority_weight",
            "wait_supply_weight",
            "wait_merchant_weight",
            "wait_priority_weight",
            "wait_reliability_weight",
            "service_score_weights",
            "priority_clip",
            "population_floor_ratio",
            "population_ceiling_ratio",
            "nonlinearity",
        }
        if not required.issubset(payload):
            fail("CONFIG_INVALID", "Layer M parameters are incomplete")
        return cls(dict(payload))

    def _number(self, name: str) -> float:
        value = self.parameters[name]
        if isinstance(value, bool) or not isinstance(value, (float, int)):
            fail("CONFIG_INVALID", f"Layer M {name} must be numeric")
        return float(value)

    @property
    def version(self) -> str:
        return str(self.parameters["model_version"])

    def symmetric_state(self, imbalance: MechanismVector) -> MechanismState:
        c0 = self._number("baseline_couriers")
        m0 = self._number("baseline_merchant_capacity")
        d0 = self._number("baseline_demand")
        return MechanismState(
            ZonePopulation(
                c0 * (1 + imbalance[0]),
                m0 * (1 + imbalance[1]),
                d0 * (1 + imbalance[2]),
            ),
            ZonePopulation(
                c0 * (1 - imbalance[0]),
                m0 * (1 - imbalance[1]),
                d0 * (1 - imbalance[2]),
            ),
        )

    def observe(self, state: MechanismState) -> MechanismVector:
        c0 = self._number("baseline_couriers")
        m0 = self._number("baseline_merchant_capacity")
        d0 = self._number("baseline_demand")
        return (
            (state.region_a.couriers - state.region_b.couriers) / (2 * c0),
            (state.region_a.merchant_capacity - state.region_b.merchant_capacity)
            / (2 * m0),
            (state.region_a.latent_demand - state.region_b.latent_demand) / (2 * d0),
        )

    def _dispatch_response(self, value: float) -> float:
        name = str(self.parameters["nonlinearity"])
        if name == "tanh":
            return tanh(value)
        if name == "logistic":
            if value >= 0:
                decay = exp(-value)
                return 4.0 * (1.0 / (1.0 + decay) - 0.5)
            growth = exp(value)
            return 4.0 * (growth / (1.0 + growth) - 0.5)
        if name == "clipped_linear":
            return max(-1.0, min(1.0, value))
        if name == "atan":
            return 2.0 * atan((pi / 2.0) * value) / pi
        fail("UNKNOWN_NONLINEARITY", name)

    @staticmethod
    def _bounded(value: float, lower: float, upper: float) -> float:
        return max(lower, min(upper, value))

    def step(
        self,
        state: MechanismState,
        alpha: float,
        *,
        rng: random.Random,
        noise_sd: float,
    ) -> tuple[MechanismState, OperationalMetrics]:
        imbalance = self.observe(state)
        weights = self.parameters["service_score_weights"]
        if not isinstance(weights, list) or len(weights) != 3:
            fail("CONFIG_INVALID", "Layer M service score weights are invalid")
        service_score = sum(
            float(weight) * value
            for weight, value in zip(weights, imbalance, strict=True)
        )
        priority = self._bounded(
            alpha * self._dispatch_response(service_score),
            -self._number("priority_clip"),
            self._number("priority_clip"),
        )
        acceptance_delta = (
            self._number("supply_acceptance_weight") * imbalance[0]
            + self._number("merchant_acceptance_weight") * imbalance[1]
            + self._number("dispatch_priority_weight") * priority
        )
        base_acceptance = self._number("base_acceptance")
        acceptance_a = self._bounded(base_acceptance + acceptance_delta, 0.05, 0.98)
        acceptance_b = self._bounded(base_acceptance - acceptance_delta, 0.05, 0.98)

        accepted_a = state.region_a.latent_demand * acceptance_a
        accepted_b = state.region_b.latent_demand * acceptance_b
        served_a = min(
            accepted_a, state.region_a.merchant_capacity, 0.9 * state.region_a.couriers
        )
        served_b = min(
            accepted_b, state.region_b.merchant_capacity, 0.9 * state.region_b.couriers
        )

        wait_shift = (
            self._number("wait_supply_weight") * imbalance[0]
            + self._number("wait_merchant_weight") * imbalance[1]
            + self._number("wait_priority_weight") * priority
        )
        wait_a = self._bounded(10.0 * (1.0 - wait_shift), 1.0, 60.0)
        wait_b = self._bounded(10.0 * (1.0 + wait_shift), 1.0, 60.0)
        opportunity_a = served_a / state.region_a.couriers
        opportunity_b = served_b / state.region_b.couriers
        utilization_a = served_a / state.region_a.merchant_capacity
        utilization_b = served_b / state.region_b.merchant_capacity
        baseline_opportunity = (
            self._number("baseline_demand")
            * base_acceptance
            / self._number("baseline_couriers")
        )
        baseline_utilization = (
            self._number("baseline_demand")
            * base_acceptance
            / self._number("baseline_merchant_capacity")
        )
        opportunity_imbalance = (opportunity_a - opportunity_b) / (
            2 * baseline_opportunity
        )
        utilization_imbalance = (utilization_a - utilization_b) / (
            2 * baseline_utilization
        )
        reliability_a = acceptance_a - self._number("wait_reliability_weight") * (
            wait_a / 10.0 - 1.0
        )
        reliability_b = acceptance_b - self._number("wait_reliability_weight") * (
            wait_b / 10.0 - 1.0
        )
        reliability_imbalance = (reliability_a - reliability_b) / 2.0

        next_imbalance = (
            self._number("courier_persistence") * imbalance[0]
            + self._number("courier_response") * opportunity_imbalance
            + rng.gauss(0.0, noise_sd),
            self._number("merchant_persistence") * imbalance[1]
            + self._number("merchant_response") * utilization_imbalance
            + rng.gauss(0.0, noise_sd),
            self._number("demand_persistence") * imbalance[2]
            + self._number("customer_response") * reliability_imbalance
            + rng.gauss(0.0, noise_sd),
        )
        lower = 1.0 - self._number("population_ceiling_ratio")
        upper = 1.0 - self._number("population_floor_ratio")
        bounded_imbalance = tuple(
            self._bounded(value, lower, upper) for value in next_imbalance
        )
        next_state = self.symmetric_state(bounded_imbalance)  # type: ignore[arg-type]
        metrics = OperationalMetrics(
            accepted_a,
            accepted_b,
            served_a,
            served_b,
            wait_a,
            wait_b,
            utilization_a,
            utilization_b,
            opportunity_a,
            opportunity_b,
            abs(served_a - served_b) / max(served_a + served_b, 1e-12),
        )
        return next_state, metrics

    def simulate(
        self,
        initial: MechanismVector,
        alpha: float,
        horizon: int,
        seed: int,
        noise_sd: float,
    ) -> MechanismRun:
        rng = random.Random(seed)
        states = [self.symmetric_state(initial)]
        observations = [self.observe(states[0])]
        metrics: list[OperationalMetrics] = []
        for _ in range(horizon):
            state, result = self.step(states[-1], alpha, rng=rng, noise_sd=noise_sd)
            states.append(state)
            observations.append(self.observe(state))
            metrics.append(result)
        return MechanismRun(
            seed, alpha, tuple(states), tuple(observations), tuple(metrics)
        )
