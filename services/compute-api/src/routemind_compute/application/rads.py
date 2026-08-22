from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from typing import Literal

from routemind_compute.application.nearest import great_circle_distance_kilometres
from routemind_compute.application.registry import StrategyRegistry
from routemind_compute.domain.dispatch import DispatchProblem

Metadata = tuple[tuple[str, str], ...]
RadsVariant = Literal["full", "distance-only", "risk-only"]

MAX_METADATA_ITEMS = 32
MAX_TEXT_LENGTH = 256
VARIANT_ORDER: dict[RadsVariant, int] = {
    "full": 0,
    "distance-only": 1,
    "risk-only": 2,
}


def _validate_text(value: str, name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must not be blank")
    if len(normalized) > MAX_TEXT_LENGTH:
        raise ValueError(f"{name} exceeds {MAX_TEXT_LENGTH} characters")
    return normalized


def _normalize_metadata(values: Metadata) -> Metadata:
    if len(values) > MAX_METADATA_ITEMS:
        raise ValueError(f"metadata exceeds {MAX_METADATA_ITEMS} items")
    normalized = tuple(
        sorted(
            (_validate_text(key, "metadata key"), _validate_text(value, "metadata value"))
            for key, value in values
        )
    )
    if len({key for key, _ in normalized}) != len(normalized):
        raise ValueError("metadata keys must be unique")
    return normalized


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _digest(payload: object) -> str:
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _validate_weight(value: float, name: str) -> None:
    if not isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class RiskSignal:
    courier_id: str
    failure_probability: float
    impact_minutes: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "courier_id", _validate_text(self.courier_id, "courier_id"))
        if not isfinite(self.failure_probability) or not 0 <= self.failure_probability <= 1:
            raise ValueError("failure_probability must be finite and between 0 and 1")
        if not isfinite(self.impact_minutes) or self.impact_minutes < 0:
            raise ValueError("impact_minutes must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class EncodedCandidate:
    courier_id: str
    distance_km: float
    failure_probability: float
    impact_minutes: float

    def __post_init__(self) -> None:
        _validate_text(self.courier_id, "courier_id")
        if not isfinite(self.distance_km) or self.distance_km < 0:
            raise ValueError("distance_km must be finite and non-negative")
        if not isfinite(self.failure_probability) or not 0 <= self.failure_probability <= 1:
            raise ValueError("failure_probability must be finite and between 0 and 1")
        if not isfinite(self.impact_minutes) or self.impact_minutes < 0:
            raise ValueError("impact_minutes must be finite and non-negative")

    def payload(self) -> dict[str, object]:
        return {
            "courier_id": self.courier_id,
            "distance_km": self.distance_km,
            "failure_probability": self.failure_probability,
            "impact_minutes": self.impact_minutes,
        }


@dataclass(frozen=True, slots=True)
class RadsState:
    request_id: str
    candidates: tuple[EncodedCandidate, ...]
    risk_multiplier: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _validate_text(self.request_id, "request_id"))
        if not isfinite(self.risk_multiplier) or self.risk_multiplier <= 0:
            raise ValueError("risk_multiplier must be finite and positive")
        candidate_ids = [candidate.courier_id for candidate in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("encoded candidate identifiers must be unique")
        object.__setattr__(
            self, "candidates", tuple(sorted(self.candidates, key=lambda item: item.courier_id))
        )

    def canonical_payload(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "risk_multiplier": self.risk_multiplier,
            "candidates": [candidate.payload() for candidate in self.candidates],
        }

    @property
    def digest(self) -> str:
        return _digest(self.canonical_payload())


class RadsStateEncoder:
    def encode(
        self,
        problem: DispatchProblem,
        risks: tuple[RiskSignal, ...],
        *,
        risk_multiplier: float = 1.0,
    ) -> RadsState:
        if not isfinite(risk_multiplier) or risk_multiplier <= 0:
            raise ValueError("risk_multiplier must be finite and positive")
        risk_by_courier: dict[str, RiskSignal] = {}
        for risk in risks:
            if risk.courier_id in risk_by_courier:
                raise ValueError("risk signal courier identifiers must be unique")
            risk_by_courier[risk.courier_id] = risk
        candidate_ids = {candidate.courier_id for candidate in problem.candidates}
        if set(risk_by_courier) != candidate_ids:
            raise ValueError("risk signals must exactly match candidate couriers")
        encoded = tuple(
            EncodedCandidate(
                candidate.courier_id,
                great_circle_distance_kilometres(
                    problem.pickup.latitude,
                    problem.pickup.longitude,
                    candidate.location.latitude,
                    candidate.location.longitude,
                ),
                risk_by_courier[candidate.courier_id].failure_probability,
                risk_by_courier[candidate.courier_id].impact_minutes,
            )
            for candidate in problem.candidates
        )
        return RadsState(problem.request_id, encoded, risk_multiplier)


@dataclass(frozen=True, slots=True)
class ObjectiveBreakdown:
    distance_km: float
    expected_risk_minutes: float
    distance_component: float
    risk_component: float
    total: float

    def payload(self) -> dict[str, float]:
        return {
            "distance_km": self.distance_km,
            "expected_risk_minutes": self.expected_risk_minutes,
            "distance_component": self.distance_component,
            "risk_component": self.risk_component,
            "total": self.total,
        }


@dataclass(frozen=True, slots=True)
class RadsObjective:
    distance_weight: float = 1.0
    risk_weight: float = 1.0

    def __post_init__(self) -> None:
        _validate_weight(self.distance_weight, "distance_weight")
        _validate_weight(self.risk_weight, "risk_weight")
        if self.distance_weight == 0 and self.risk_weight == 0:
            raise ValueError("at least one objective weight must be positive")

    def evaluate(
        self,
        candidate: EncodedCandidate,
        *,
        risk_multiplier: float,
        variant: RadsVariant = "full",
    ) -> ObjectiveBreakdown:
        if variant not in VARIANT_ORDER:
            raise ValueError(f"unknown RADS variant: {variant}")
        if not isfinite(risk_multiplier) or risk_multiplier <= 0:
            raise ValueError("risk_multiplier must be finite and positive")
        expected_risk = candidate.failure_probability * candidate.impact_minutes * risk_multiplier
        distance_component = (
            0.0 if variant == "risk-only" else self.distance_weight * candidate.distance_km
        )
        risk_component = 0.0 if variant == "distance-only" else self.risk_weight * expected_risk
        return ObjectiveBreakdown(
            candidate.distance_km,
            expected_risk,
            distance_component,
            risk_component,
            distance_component + risk_component,
        )


@dataclass(frozen=True, slots=True)
class RadsSelection:
    request_id: str
    variant: RadsVariant
    courier_id: str | None
    score: float | None
    breakdown: ObjectiveBreakdown | None
    explanation: tuple[str, ...]
    state_digest: str

    def __post_init__(self) -> None:
        _validate_text(self.request_id, "request_id")
        if self.variant not in VARIANT_ORDER:
            raise ValueError(f"unknown RADS variant: {self.variant}")
        if self.courier_id is None:
            if self.score is not None or self.breakdown is not None:
                raise ValueError("unassigned selection cannot have a score breakdown")
        else:
            _validate_text(self.courier_id, "courier_id")
            if self.score is None or self.breakdown is None:
                raise ValueError("assigned selection requires a score breakdown")
        if not self.explanation or any(not item.strip() for item in self.explanation):
            raise ValueError("selection explanation must contain non-blank items")
        if len(self.state_digest) != 64:
            raise ValueError("state_digest must be a SHA-256 digest")

    def payload(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "variant": self.variant,
            "courier_id": self.courier_id,
            "score": self.score,
            "breakdown": self.breakdown.payload() if self.breakdown else None,
            "explanation": self.explanation,
            "state_digest": self.state_digest,
        }


class RadsSelector:
    def __init__(self, objective: RadsObjective) -> None:
        self.objective = objective

    def select(self, state: RadsState, *, variant: RadsVariant = "full") -> RadsSelection:
        if variant not in VARIANT_ORDER:
            raise ValueError(f"unknown RADS variant: {variant}")
        if not state.candidates:
            return RadsSelection(
                state.request_id,
                variant,
                None,
                None,
                None,
                ("no eligible courier", f"variant={variant}"),
                state.digest,
            )
        ranked = sorted(
            (
                (
                    self.objective.evaluate(
                        candidate,
                        risk_multiplier=state.risk_multiplier,
                        variant=variant,
                    ),
                    candidate,
                )
                for candidate in state.candidates
            ),
            key=lambda item: (item[0].total, item[1].courier_id),
        )
        breakdown, candidate = ranked[0]
        explanation = (
            f"variant={variant}",
            f"distance_km={candidate.distance_km:.6f}",
            f"failure_probability={candidate.failure_probability:.6f}",
            f"impact_minutes={candidate.impact_minutes:.6f}",
            f"risk_multiplier={state.risk_multiplier:.6f}",
            f"objective={breakdown.total:.6f}",
        )
        return RadsSelection(
            state.request_id,
            variant,
            candidate.courier_id,
            breakdown.total,
            breakdown,
            explanation,
            state.digest,
        )


@dataclass(frozen=True, slots=True)
class RadsExperimentManifest:
    manifest_id: str
    code_version: str
    scenario_id: str
    seed: int
    baselines: tuple[str, ...]
    distance_weight: float
    risk_weight: float
    variants: tuple[RadsVariant, ...] = ("full", "distance-only", "risk-only")
    risk_multipliers: tuple[float, ...] = (1.0,)
    configuration: Metadata = ()

    def __post_init__(self) -> None:
        for field_name in ("manifest_id", "code_version", "scenario_id"):
            object.__setattr__(
                self, field_name, _validate_text(getattr(self, field_name), field_name)
            )
        if not self.baselines:
            raise ValueError("at least one baseline is required")
        baselines = tuple(sorted(_validate_text(item, "baseline") for item in self.baselines))
        if len(baselines) != len(set(baselines)):
            raise ValueError("baseline names must be unique")
        if not self.variants:
            raise ValueError("at least one RADS variant is required")
        if any(variant not in VARIANT_ORDER for variant in self.variants):
            raise ValueError("RADS variants contain an unknown value")
        if len(self.variants) != len(set(self.variants)):
            raise ValueError("RADS variants must be unique")
        if not self.risk_multipliers:
            raise ValueError("at least one risk multiplier is required")
        if any(not isfinite(value) or value <= 0 for value in self.risk_multipliers):
            raise ValueError("risk multipliers must be finite and positive")
        if len(self.risk_multipliers) != len(set(self.risk_multipliers)):
            raise ValueError("risk multipliers must be unique")
        RadsObjective(self.distance_weight, self.risk_weight)
        object.__setattr__(self, "baselines", baselines)
        object.__setattr__(
            self, "variants", tuple(sorted(self.variants, key=VARIANT_ORDER.__getitem__))
        )
        object.__setattr__(self, "risk_multipliers", tuple(sorted(self.risk_multipliers)))
        object.__setattr__(self, "configuration", _normalize_metadata(self.configuration))

    def canonical_payload(self) -> dict[str, object]:
        return {
            "manifest_id": self.manifest_id,
            "code_version": self.code_version,
            "scenario_id": self.scenario_id,
            "seed": self.seed,
            "baselines": self.baselines,
            "distance_weight": self.distance_weight,
            "risk_weight": self.risk_weight,
            "variants": self.variants,
            "risk_multipliers": self.risk_multipliers,
            "configuration": self.configuration,
        }

    @property
    def digest(self) -> str:
        return _digest(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class BaselineResult:
    strategy: str
    strategy_version: str
    courier_id: str | None
    score: float | None
    rationale: tuple[str, ...]

    def payload(self) -> dict[str, object]:
        return {
            "strategy": self.strategy,
            "strategy_version": self.strategy_version,
            "courier_id": self.courier_id,
            "score": self.score,
            "rationale": self.rationale,
        }


@dataclass(frozen=True, slots=True)
class RadsTrial:
    risk_multiplier: float
    variant: RadsVariant
    selection: RadsSelection

    def __post_init__(self) -> None:
        if self.variant != self.selection.variant:
            raise ValueError("trial variant does not match selection")
        if not isfinite(self.risk_multiplier) or self.risk_multiplier <= 0:
            raise ValueError("risk_multiplier must be finite and positive")

    def payload(self) -> dict[str, object]:
        return {
            "risk_multiplier": self.risk_multiplier,
            "variant": self.variant,
            "selection": self.selection.payload(),
        }


@dataclass(frozen=True, slots=True)
class RadsExperimentRun:
    manifest: RadsExperimentManifest
    baselines: tuple[BaselineResult, ...]
    trials: tuple[RadsTrial, ...]
    output_digest: str

    def __post_init__(self) -> None:
        if not self.baselines:
            raise ValueError("experiment run must contain baseline results")
        if not self.trials:
            raise ValueError("experiment run must contain RADS trials")
        if len(self.output_digest) != 64:
            raise ValueError("output_digest must be a SHA-256 digest")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "manifest": self.manifest.canonical_payload(),
            "baselines": [result.payload() for result in self.baselines],
            "trials": [trial.payload() for trial in self.trials],
            "output_digest": self.output_digest,
        }

    def metrics(self) -> tuple[dict[str, object], ...]:
        return tuple(
            {
                "variant": trial.variant,
                "risk_multiplier": trial.risk_multiplier,
                "courier_id": trial.selection.courier_id,
                "score": trial.selection.score,
                "distance_component": (
                    trial.selection.breakdown.distance_component
                    if trial.selection.breakdown
                    else None
                ),
                "risk_component": (
                    trial.selection.breakdown.risk_component if trial.selection.breakdown else None
                ),
                "state_digest": trial.selection.state_digest,
            }
            for trial in self.trials
        )


class RadsExperimentRunner:
    def __init__(self, registry: StrategyRegistry) -> None:
        self.registry = registry
        self.encoder = RadsStateEncoder()

    def run(
        self,
        manifest: RadsExperimentManifest,
        problem: DispatchProblem,
        risks: tuple[RiskSignal, ...],
    ) -> RadsExperimentRun:
        baselines = tuple(
            self._baseline_result(self.registry.solve(strategy, problem))
            for strategy in manifest.baselines
        )
        selector = RadsSelector(RadsObjective(manifest.distance_weight, manifest.risk_weight))
        trials: list[RadsTrial] = []
        for multiplier in manifest.risk_multipliers:
            state = self.encoder.encode(problem, risks, risk_multiplier=multiplier)
            for variant in manifest.variants:
                selection = selector.select(state, variant=variant)
                trials.append(RadsTrial(multiplier, variant, selection))
        deterministic = {
            "manifest_digest": manifest.digest,
            "baselines": [result.payload() for result in baselines],
            "trials": [trial.payload() for trial in trials],
        }
        return RadsExperimentRun(manifest, baselines, tuple(trials), _digest(deterministic))

    @staticmethod
    def _baseline_result(decision: object) -> BaselineResult:
        from routemind_compute.domain.dispatch import DispatchDecision

        if not isinstance(decision, DispatchDecision):
            raise TypeError("registry returned an invalid dispatch decision")
        return BaselineResult(
            decision.strategy,
            decision.strategy_version,
            decision.courier_id,
            decision.score,
            decision.rationale,
        )
