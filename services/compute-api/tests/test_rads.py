from __future__ import annotations

from math import inf, nan

import pytest

from routemind_compute.application.baselines import WeightedGreedyStrategy
from routemind_compute.application.nearest import NearestStrategy
from routemind_compute.application.rads import (
    BaselineResult,
    EncodedCandidate,
    ObjectiveBreakdown,
    RadsExperimentManifest,
    RadsExperimentRun,
    RadsExperimentRunner,
    RadsObjective,
    RadsSelection,
    RadsSelector,
    RadsState,
    RadsStateEncoder,
    RadsTrial,
    RiskSignal,
)
from routemind_compute.application.registry import StrategyRegistry
from routemind_compute.domain.dispatch import CourierCandidate, DispatchProblem, GeoPoint


def problem() -> DispatchProblem:
    return DispatchProblem(
        "request-rads",
        GeoPoint(31.2304, 121.4737),
        (
            CourierCandidate("courier-near-risky", GeoPoint(31.2305, 121.4738)),
            CourierCandidate("courier-far-safe", GeoPoint(31.2350, 121.4780)),
        ),
    )


def risks() -> tuple[RiskSignal, ...]:
    return (
        RiskSignal("courier-near-risky", 0.8, 20.0),
        RiskSignal("courier-far-safe", 0.01, 5.0),
    )


def manifest(**overrides: object) -> RadsExperimentManifest:
    values: dict[str, object] = {
        "manifest_id": "rads-manifest-1",
        "code_version": "git:e11a0ac",
        "scenario_id": "rads-reduced",
        "seed": 17,
        "baselines": ("weighted-greedy", "nearest"),
        "distance_weight": 1.0,
        "risk_weight": 2.0,
        "risk_multipliers": (2.0, 1.0),
        "configuration": (("fixture", "two-couriers"),),
    }
    values.update(overrides)
    return RadsExperimentManifest(**values)  # type: ignore[arg-type]


def runner() -> RadsExperimentRunner:
    return RadsExperimentRunner(StrategyRegistry((NearestStrategy(), WeightedGreedyStrategy())))


def test_state_encoder_is_canonical_and_requires_exact_finite_risk_profile() -> None:
    encoder = RadsStateEncoder()
    first = encoder.encode(problem(), risks(), risk_multiplier=1.5)
    second = encoder.encode(problem(), tuple(reversed(risks())), risk_multiplier=1.5)

    assert first == second
    assert first.digest == second.digest
    assert [item.courier_id for item in first.candidates] == [
        "courier-far-safe",
        "courier-near-risky",
    ]
    assert first.canonical_payload()["risk_multiplier"] == 1.5

    with pytest.raises(ValueError, match="exactly match"):
        encoder.encode(problem(), risks()[:1])
    with pytest.raises(ValueError, match="unique"):
        encoder.encode(problem(), (risks()[0], risks()[0]))
    with pytest.raises(ValueError, match="risk_multiplier"):
        encoder.encode(problem(), risks(), risk_multiplier=0)
    with pytest.raises(ValueError, match="failure_probability"):
        RiskSignal("courier", nan, 1.0)
    with pytest.raises(ValueError, match="failure_probability"):
        RiskSignal("courier", 1.1, 1.0)
    with pytest.raises(ValueError, match="impact_minutes"):
        RiskSignal("courier", 0.1, inf)


def test_objective_selector_exposes_components_explanations_and_stable_ties() -> None:
    state = RadsStateEncoder().encode(problem(), risks())
    objective = RadsObjective(distance_weight=1.0, risk_weight=2.0)
    selector = RadsSelector(objective)

    full = selector.select(state)
    distance_only = selector.select(state, variant="distance-only")
    risk_only = selector.select(state, variant="risk-only")

    assert full.courier_id == "courier-far-safe"
    assert distance_only.courier_id == "courier-near-risky"
    assert risk_only.courier_id == "courier-far-safe"
    assert full.breakdown is not None
    assert full.score == full.breakdown.total
    assert full.breakdown.risk_component == pytest.approx(0.1)
    assert any(item.startswith("objective=") for item in full.explanation)
    assert full.payload()["state_digest"] == state.digest

    tied = RadsState(
        "request-tie",
        (
            EncodedCandidate("courier-b", 1.0, 0.1, 1.0),
            EncodedCandidate("courier-a", 1.0, 0.1, 1.0),
        ),
        1.0,
    )
    assert selector.select(tied).courier_id == "courier-a"

    empty = selector.select(RadsState("request-empty", (), 1.0))
    assert empty.courier_id is None
    assert empty.score is None
    assert empty.explanation[0] == "no eligible courier"


def test_experiment_compares_baselines_ablation_and_robustness_reproducibly() -> None:
    first = runner().run(manifest(), problem(), risks())
    second = runner().run(manifest(), problem(), risks())

    assert first.output_digest == second.output_digest
    assert [item.strategy for item in first.baselines] == ["nearest", "weighted-greedy"]
    assert len(first.trials) == 6
    assert {item.variant for item in first.trials} == {
        "full",
        "distance-only",
        "risk-only",
    }
    assert {item.risk_multiplier for item in first.trials} == {1.0, 2.0}
    assert len({item.selection.state_digest for item in first.trials}) == 2
    assert all("distance_component" in metric for metric in first.metrics())
    assert first.canonical_payload()["output_digest"] == first.output_digest

    robust = runner().run(manifest(risk_multipliers=(3.0,)), problem(), risks())
    assert robust.output_digest != first.output_digest
    assert robust.manifest.digest != first.manifest.digest


def test_manifest_and_result_validation_reject_invalid_experiment_inputs() -> None:
    value = manifest()
    assert value.baselines == ("nearest", "weighted-greedy")
    assert value.risk_multipliers == (1.0, 2.0)
    assert value.variants == ("full", "distance-only", "risk-only")
    assert len(value.digest) == 64

    with pytest.raises(ValueError, match="baseline"):
        manifest(baselines=())
    with pytest.raises(ValueError, match="unique"):
        manifest(baselines=("nearest", "nearest"))
    with pytest.raises(ValueError, match="variant"):
        manifest(variants=())
    with pytest.raises(ValueError, match="unknown"):
        manifest(variants=("other",))
    with pytest.raises(ValueError, match="risk multiplier"):
        manifest(risk_multipliers=(0.0,))
    with pytest.raises(ValueError, match="unique"):
        manifest(risk_multipliers=(1.0, 1.0))
    with pytest.raises(ValueError, match="objective weight"):
        manifest(distance_weight=0.0, risk_weight=0.0)
    with pytest.raises(ValueError, match="metadata keys"):
        manifest(configuration=(("x", "1"), ("x", "2")))

    selection = RadsSelector(RadsObjective()).select(RadsStateEncoder().encode(problem(), risks()))
    with pytest.raises(ValueError, match="variant"):
        RadsTrial(1.0, "risk-only", selection)
    with pytest.raises(ValueError, match="baseline results"):
        RadsExperimentRun(value, (), (RadsTrial(1.0, "full", selection),), "a" * 64)
    with pytest.raises(ValueError, match="RADS trials"):
        RadsExperimentRun(
            value,
            (BaselineResult("nearest", "1.0.0", None, None, ("none",)),),
            (),
            "a" * 64,
        )


def test_low_level_validation_rejects_non_finite_and_inconsistent_values() -> None:
    candidate = EncodedCandidate("courier", 1.0, 0.2, 5.0)
    with pytest.raises(ValueError, match="distance_km"):
        EncodedCandidate("courier", inf, 0.2, 5.0)
    with pytest.raises(ValueError, match="failure_probability"):
        EncodedCandidate("courier", 1.0, -0.1, 5.0)
    with pytest.raises(ValueError, match="impact_minutes"):
        EncodedCandidate("courier", 1.0, 0.2, -1.0)
    with pytest.raises(ValueError, match="finite"):
        RadsObjective(inf, 1.0)
    with pytest.raises(ValueError, match="positive"):
        RadsObjective().evaluate(candidate, risk_multiplier=0)
    with pytest.raises(ValueError, match="unknown RADS variant"):
        RadsSelector(RadsObjective()).select(
            RadsState("request", (candidate,), 1.0),
            variant="other",  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="score breakdown"):
        RadsSelection("request", "full", None, 1.0, None, ("reason",), "a" * 64)
    with pytest.raises(ValueError, match="score breakdown"):
        RadsSelection("request", "full", "courier", None, None, ("reason",), "a" * 64)
    with pytest.raises(ValueError, match="SHA-256"):
        RadsSelection(
            "request",
            "full",
            "courier",
            1.0,
            ObjectiveBreakdown(1.0, 0.1, 1.0, 0.1, 1.1),
            ("reason",),
            "short",
        )
