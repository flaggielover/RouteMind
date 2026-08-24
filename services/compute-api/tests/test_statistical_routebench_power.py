from __future__ import annotations

from dataclasses import replace
from importlib.metadata import version
from pathlib import Path
from typing import Literal

import pytest
from scipy.stats import nct as scipy_nct

from routemind_compute.application import statistical_routebench_power as power_module
from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.statistical_routebench_power import (
    PilotVarianceInput,
    ProspectivePowerError,
    paired_t_power,
    plan_primary_power,
    solve_paired_t_sample_size,
)
from routemind_compute.application.statistical_routebench_protocol import (
    StatisticalRouteBenchProtocol,
    load_statistical_routebench_protocol,
)

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = (
    ROOT
    / "docs"
    / "research"
    / "r3"
    / "manifests"
    / "statistical-routebench"
    / "statistical-routebench-v1.json"
)
SOURCE_DIGEST = canonical_digest({"fixture": "synthetic-paired-variance-v1"})


@pytest.fixture(scope="module")
def protocol() -> StatisticalRouteBenchProtocol:
    return load_statistical_routebench_protocol(PROTOCOL_PATH)


def pilot(
    protocol: StatisticalRouteBenchProtocol,
    *,
    metric_id: str = "scenario_risk_index",
    variance: float = 0.0016,
    regime_id: str = "normal",
    source_kind: Literal["synthetic_validation", "r3_325_pilot"] = "synthetic_validation",
    pair_count: int = 8,
) -> PilotVarianceInput:
    return PilotVarianceInput(
        protocol.protocol_id,
        regime_id,
        metric_id,
        pair_count,
        variance,
        source_kind,
        SOURCE_DIGEST,
    )


def test_scipy_runtime_is_exactly_locked() -> None:
    assert version("scipy") == "1.18.0"


def test_pilot_payload_is_canonical_input_record(
    protocol: StatisticalRouteBenchProtocol,
) -> None:
    source = pilot(protocol)

    assert source.payload() == {
        "protocol_id": protocol.protocol_id,
        "regime_id": "normal",
        "metric_id": "scenario_risk_index",
        "pilot_pair_count": 8,
        "paired_variance": 0.0016,
        "source_kind": "synthetic_validation",
        "source_digest": SOURCE_DIGEST,
    }


def test_one_sided_paired_t_reference_vector() -> None:
    assert paired_t_power(26, 0.5, 0.05) == pytest.approx(0.7980537143957398, abs=1e-14)
    assert paired_t_power(27, 0.5, 0.05) > 0.8
    assert solve_paired_t_sample_size(0.5, 0.05, 0.8) == 27


@pytest.mark.parametrize(
    ("metric_id", "null_boundary", "alternative"),
    (("scenario_risk_index", 0.0, -0.02), ("assignment_rate", -0.02, 0.0)),
)
def test_protocol_plan_records_every_input_and_conservative_holm_alpha(
    protocol: StatisticalRouteBenchProtocol,
    metric_id: str,
    null_boundary: float,
    alternative: float,
) -> None:
    result = plan_primary_power(protocol, pilot(protocol, metric_id=metric_id))

    assert result.pilot_pair_count == 8
    assert result.pilot_paired_variance == pytest.approx(0.0016)
    assert result.pilot_standard_deviation == pytest.approx(0.04)
    assert result.variance_source_kind == "synthetic_validation"
    assert not result.observed_pilot
    assert result.null_boundary == pytest.approx(null_boundary)
    assert result.planning_alternative == pytest.approx(alternative)
    assert result.effect_distance_from_null == pytest.approx(0.02)
    assert result.standardized_effect_size == pytest.approx(0.5)
    assert result.familywise_alpha == pytest.approx(0.05)
    assert result.confirmatory_test_count == 16
    assert result.local_alpha == pytest.approx(0.003125)
    assert result.target_power == pytest.approx(0.8)
    assert result.minimum_pair_count == 20
    assert result.maximum_pair_count == 200
    assert result.round_up_to_pairs == 4
    assert result.raw_required_pair_count == 55
    assert result.required_pair_count == 56
    assert result.planned_pair_count == 56
    assert result.power_at_required_count == pytest.approx(0.8104064287044574)
    assert result.disposition == "POWER_TARGET_MET_WITHIN_CAP"
    assert result.scipy_version == "1.18.0"
    assert result.claim_boundary == "PROSPECTIVE_DESIGN_NOT_OBSERVED_EFFECT"
    assert len(result.plan_digest) == 64


def test_underpowered_plan_retains_required_count_and_cap_power(
    protocol: StatisticalRouteBenchProtocol,
) -> None:
    result = plan_primary_power(protocol, pilot(protocol, variance=0.01))

    assert result.standardized_effect_size == pytest.approx(0.2)
    assert result.raw_required_pair_count == 324
    assert result.required_pair_count == 324
    assert result.planned_pair_count == 200
    assert result.power_at_required_count == pytest.approx(0.8008824543088078)
    assert result.power_at_cap == pytest.approx(0.5269065070498481)
    assert result.disposition == "UNDERPOWERED_AT_CAP"


def test_observed_pilot_requires_frozen_count_and_is_labeled(
    protocol: StatisticalRouteBenchProtocol,
) -> None:
    observed = plan_primary_power(
        protocol, pilot(protocol, source_kind="r3_325_pilot", pair_count=8)
    )
    assert observed.observed_pilot

    with pytest.raises(ProspectivePowerError, match="exactly the frozen"):
        plan_primary_power(protocol, pilot(protocol, source_kind="r3_325_pilot", pair_count=7))


def test_plan_rejects_scipy_runtime_drift(
    protocol: StatisticalRouteBenchProtocol, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(power_module, "version", lambda _package: "1.18.1")

    with pytest.raises(ProspectivePowerError, match="SciPy runtime identity"):
        plan_primary_power(protocol, pilot(protocol))


def test_plan_is_digest_stable_and_sensitive_to_variance(
    protocol: StatisticalRouteBenchProtocol,
) -> None:
    first = plan_primary_power(protocol, pilot(protocol))
    second = plan_primary_power(protocol, pilot(protocol))
    changed = plan_primary_power(protocol, pilot(protocol, variance=0.0025))

    assert first == second
    assert first.plan_digest == second.plan_digest
    assert first.plan_digest != changed.plan_digest
    assert changed.required_pair_count > first.required_pair_count


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("protocol_id", "other", "protocol"),
        ("regime_id", "other", "regime"),
        ("metric_id", "runtime_millis", "primary metrics"),
    ),
)
def test_plan_rejects_identity_drift(
    protocol: StatisticalRouteBenchProtocol, field: str, value: str, message: str
) -> None:
    source = pilot(protocol)
    if field == "protocol_id":
        drifted = replace(source, protocol_id=value)
    elif field == "regime_id":
        drifted = replace(source, regime_id=value)
    else:
        drifted = replace(source, metric_id=value)

    with pytest.raises(ProspectivePowerError, match=message):
        plan_primary_power(protocol, drifted)


@pytest.mark.parametrize(
    ("pair_count", "variance", "source_kind", "source_digest", "message"),
    (
        (1, 0.1, "synthetic_validation", SOURCE_DIGEST, "at least two"),
        (True, 0.1, "synthetic_validation", SOURCE_DIGEST, "at least two"),
        (8, 0.0, "synthetic_validation", SOURCE_DIGEST, "positive"),
        (8, float("nan"), "synthetic_validation", SOURCE_DIGEST, "positive"),
        (8, True, "synthetic_validation", SOURCE_DIGEST, "positive"),
        (8, 0.1, "other", SOURCE_DIGEST, "unsupported"),
        (8, 0.1, "synthetic_validation", "BAD", "SHA-256"),
    ),
)
def test_pilot_variance_input_fails_closed(
    protocol: StatisticalRouteBenchProtocol,
    pair_count: int,
    variance: float,
    source_kind: str,
    source_digest: str,
    message: str,
) -> None:
    with pytest.raises(ProspectivePowerError, match=message):
        PilotVarianceInput(
            protocol.protocol_id,
            "normal",
            "scenario_risk_index",
            pair_count,
            variance,
            source_kind,  # type: ignore[arg-type]
            source_digest,
        )


@pytest.mark.parametrize("blank_field", ("protocol_id", "regime_id", "metric_id"))
def test_pilot_variance_input_rejects_blank_identity(
    protocol: StatisticalRouteBenchProtocol, blank_field: str
) -> None:
    source = pilot(protocol)

    with pytest.raises(ProspectivePowerError, match="identities"):
        if blank_field == "protocol_id":
            replace(source, protocol_id=" ")
        elif blank_field == "regime_id":
            replace(source, regime_id=" ")
        else:
            replace(source, metric_id=" ")


@pytest.mark.parametrize(
    ("pair_count", "effect", "alpha", "message"),
    (
        (1, 0.5, 0.05, "at least two"),
        (True, 0.5, 0.05, "at least two"),
        (20, 0.0, 0.05, "effect"),
        (20, float("nan"), 0.05, "effect"),
        (20, 0.5, 0.0, "alpha"),
        (20, 0.5, 0.5, "alpha"),
        (20, 0.5, True, "alpha"),
    ),
)
def test_paired_t_power_rejects_invalid_inputs(
    pair_count: int, effect: float, alpha: float, message: str
) -> None:
    with pytest.raises(ProspectivePowerError, match=message):
        paired_t_power(pair_count, effect, alpha)


def test_paired_t_power_rejects_invalid_numeric_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scipy_nct, "sf", lambda *_args: float("nan"))

    with pytest.raises(ProspectivePowerError, match="invalid value"):
        paired_t_power(20, 0.5, 0.05)


@pytest.mark.parametrize("target", (0.0, 0.5, 1.0, float("nan")))
def test_solver_rejects_invalid_target_power(target: float) -> None:
    with pytest.raises(ProspectivePowerError, match="target power"):
        solve_paired_t_sample_size(0.5, 0.05, target)


@pytest.mark.parametrize(
    ("effect", "alpha", "minimum", "message"),
    (
        (0.0, 0.05, 2, "effect"),
        (0.5, 0.0, 2, "alpha"),
        (0.5, 0.05, 1, "at least two"),
    ),
)
def test_solver_rejects_invalid_design_inputs(
    effect: float, alpha: float, minimum: int, message: str
) -> None:
    with pytest.raises(ProspectivePowerError, match=message):
        solve_paired_t_sample_size(effect, alpha, 0.8, minimum)


def test_solver_returns_minimum_when_it_already_meets_power() -> None:
    assert solve_paired_t_sample_size(10.0, 0.05, 0.8, 2) == 2


def test_solver_fails_when_required_count_exceeds_numerical_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(power_module, "paired_t_power", lambda *_args: 0.0)

    with pytest.raises(ProspectivePowerError, match="numerical planning range"):
        solve_paired_t_sample_size(0.5, 0.05, 0.8)


def test_solver_rejects_overflowing_normal_bracket() -> None:
    with pytest.raises(ProspectivePowerError, match="numerical planning range"):
        solve_paired_t_sample_size(1e-300, 0.05, 0.8)


def test_plan_rejects_nonpositive_rounding_increment(
    protocol: StatisticalRouteBenchProtocol,
) -> None:
    invalid_protocol = replace(protocol, round_up_to_pairs=0)

    with pytest.raises(ProspectivePowerError, match="rounding increment"):
        plan_primary_power(invalid_protocol, pilot(invalid_protocol))
