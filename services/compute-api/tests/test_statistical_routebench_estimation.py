from __future__ import annotations

from dataclasses import replace
from math import sqrt
from pathlib import Path

import pytest

from routemind_compute.application.statistical_routebench_estimation import (
    PairedEstimationError,
    PairedMetricSpec,
    PairedObservation,
    estimate_paired,
    student_t_cdf,
    student_t_quantile,
)
from routemind_compute.application.statistical_routebench_protocol import (
    StatisticalRouteBenchProtocol,
    load_statistical_routebench_protocol,
)
from routemind_compute.application.statistical_routebench_randomness import (
    CommonRandomNumberPlan,
    build_common_random_number_plan,
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


@pytest.fixture(scope="module")
def protocol() -> StatisticalRouteBenchProtocol:
    return load_statistical_routebench_protocol(PROTOCOL_PATH)


def observations_for(
    protocol: StatisticalRouteBenchProtocol,
    differences: tuple[float, ...],
    *,
    regime: str = "normal",
    start: int = 1000,
) -> tuple[PairedObservation, ...]:
    return tuple(
        PairedObservation(
            build_common_random_number_plan(protocol, "confirmatory", regime, start + index),
            difference,
            0.0,
        )
        for index, difference in enumerate(differences)
    )


@pytest.mark.parametrize(
    ("degrees_of_freedom", "critical"),
    (
        (1, 12.7062047364321),
        (2, 4.30265272969614),
        (5, 2.57058183563631),
        (10, 2.22813885196494),
        (30, 2.04227245630124),
    ),
)
def test_student_t_quantile_matches_reference_values(
    degrees_of_freedom: int, critical: float
) -> None:
    value = student_t_quantile(0.975, degrees_of_freedom)
    assert value == pytest.approx(critical, rel=5e-11, abs=5e-10)
    assert student_t_cdf(value, degrees_of_freedom) == pytest.approx(0.975, abs=2e-13)
    assert student_t_quantile(0.025, degrees_of_freedom) == pytest.approx(-value, abs=1e-14)


def test_paired_estimate_reports_every_frozen_primary_and_sensitivity_field(
    protocol: StatisticalRouteBenchProtocol,
) -> None:
    result = estimate_paired(
        PairedMetricSpec("scenario_risk_index"),
        observations_for(protocol, (1.0, 2.0, 3.0, 4.0, 5.0)),
    )

    assert result.n == 5
    assert result.mean_difference == pytest.approx(3.0)
    assert result.median_difference == pytest.approx(3.0)
    assert result.standard_deviation == pytest.approx(sqrt(2.5))
    assert result.interval.degrees_of_freedom == 4
    assert result.interval.critical_value == pytest.approx(2.7764451051977987)
    assert result.interval.standard_error == pytest.approx(sqrt(0.5))
    assert result.interval.lower == pytest.approx(1.036756838522439)
    assert result.interval.upper == pytest.approx(4.9632431614775605)
    assert result.cohens_dz == pytest.approx(3.0 / sqrt(2.5))
    assert result.ten_percent_winsorized_mean == pytest.approx(3.0)
    assert tuple(item.mean_difference for item in result.leave_one_pair_out) == pytest.approx(
        (3.5, 3.25, 3.0, 2.75, 2.5)
    )
    assert result.leave_one_pair_out_minimum == pytest.approx(2.5)
    assert result.leave_one_pair_out_maximum == pytest.approx(3.5)
    assert result.leave_one_pair_out_max_absolute_shift == pytest.approx(0.5)
    assert result.difference_convention == "candidate_minus_comparator"
    assert result.sensitivity_disposition == "SENSITIVITY_CANNOT_REPLACE_PRIMARY"
    assert (
        result.report_digest == "8cc4f549a880f1563b3b2dbe4a3a4e6867b6ece7c2f4166a469f6311fafe585c"
    )


def test_seed_lineage_is_complete_sorted_and_order_invariant(
    protocol: StatisticalRouteBenchProtocol,
) -> None:
    source = observations_for(protocol, (0.3, 0.1, 0.2), regime="surge")
    forward = estimate_paired(PairedMetricSpec("runtime_millis"), source)
    reverse = estimate_paired(PairedMetricSpec("runtime_millis"), tuple(reversed(source)))

    assert forward == reverse
    assert forward.report_digest == reverse.report_digest
    assert tuple(item.replicate for item in forward.pair_seeds) == (1000, 1001, 1002)
    assert all(
        tuple(stream[0] for stream in item.streams) == ("demand", "merchant", "courier", "traffic")
        for item in forward.pair_seeds
    )
    assert all(len({stream[1] for stream in item.streams}) == 4 for item in forward.pair_seeds)
    assert all(len(item.plan_digest) == 64 for item in forward.pair_seeds)
    assert len(forward.report_digest) == 64


def test_winsorized_and_leave_one_out_sensitivity_expose_an_outlier(
    protocol: StatisticalRouteBenchProtocol,
) -> None:
    result = estimate_paired(
        PairedMetricSpec("runtime_millis", minimum=0.0),
        observations_for(protocol, (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 100.0)),
    )

    assert result.mean_difference == pytest.approx(10.0)
    assert result.median_difference == pytest.approx(0.0)
    assert result.ten_percent_winsorized_mean == pytest.approx(0.0)
    assert result.leave_one_pair_out_minimum == pytest.approx(0.0)
    assert result.leave_one_pair_out_maximum == pytest.approx(100.0 / 9.0)
    assert result.leave_one_pair_out_max_absolute_shift == pytest.approx(10.0)


@pytest.mark.parametrize(
    "differences",
    ((), (0.1,), (0.1, 0.1), (0.0, -0.0)),
)
def test_incomplete_and_zero_variance_samples_fail_explicitly(
    protocol: StatisticalRouteBenchProtocol, differences: tuple[float, ...]
) -> None:
    with pytest.raises(PairedEstimationError, match=r"at least two|zero variance"):
        estimate_paired(
            PairedMetricSpec("assignment_rate"), observations_for(protocol, differences)
        )


@pytest.mark.parametrize("value", (float("nan"), float("inf"), float("-inf"), True))
def test_non_finite_and_boolean_arm_values_are_rejected(
    protocol: StatisticalRouteBenchProtocol, value: float
) -> None:
    plan = build_common_random_number_plan(protocol, "pilot", "normal", 0)
    with pytest.raises(PairedEstimationError, match="finite numbers"):
        PairedObservation(plan, value, 0.0)


def test_duplicate_and_mixed_pair_samples_fail_closed(
    protocol: StatisticalRouteBenchProtocol,
) -> None:
    first, second = observations_for(protocol, (0.1, 0.2))
    with pytest.raises(PairedEstimationError, match="duplicate"):
        estimate_paired(PairedMetricSpec("risk"), (first, replace(first, candidate_value=0.3)))

    other_regime = observations_for(protocol, (0.3,), regime="surge")[0]
    with pytest.raises(PairedEstimationError, match="share protocol"):
        estimate_paired(PairedMetricSpec("risk"), (first, other_regime))

    pilot = PairedObservation(
        build_common_random_number_plan(protocol, "pilot", "normal", 1), 0.4, 0.0
    )
    with pytest.raises(PairedEstimationError, match="share protocol"):
        estimate_paired(PairedMetricSpec("risk"), (second, pilot))


def test_mixed_protocol_identity_fails_closed(protocol: StatisticalRouteBenchProtocol) -> None:
    first, second = observations_for(protocol, (0.1, 0.2))
    pair = replace(second.plan.pair, protocol_id="other-protocol")
    drifted_plan = CommonRandomNumberPlan(
        pair,
        tuple(replace(stream, pair=pair) for stream in second.plan.streams),
    )
    with pytest.raises(PairedEstimationError, match="share protocol"):
        estimate_paired(
            PairedMetricSpec("risk"),
            (
                first,
                PairedObservation(drifted_plan, second.candidate_value, second.comparator_value),
            ),
        )


@pytest.mark.parametrize(("field", "message"), (("seed", "seed"), ("digest", "digest")))
def test_forged_stream_lineage_fails_closed(
    protocol: StatisticalRouteBenchProtocol, field: str, message: str
) -> None:
    first, second = observations_for(protocol, (0.1, 0.2))
    stream = second.plan.streams[0]
    drifted = (
        replace(stream, seed=stream.seed + 1)
        if field == "seed"
        else replace(stream, stream_digest="f" * 64)
    )
    plan = CommonRandomNumberPlan(second.plan.pair, (drifted, *second.plan.streams[1:]))
    with pytest.raises(PairedEstimationError, match=message):
        estimate_paired(
            PairedMetricSpec("risk"),
            (first, PairedObservation(plan, second.candidate_value, second.comparator_value)),
        )


@pytest.mark.parametrize(
    ("candidate", "comparator", "message"),
    ((-0.01, 0.2, "below"), (0.2, 1.01, "exceeds")),
)
def test_metric_bounds_apply_to_both_arms(
    protocol: StatisticalRouteBenchProtocol,
    candidate: float,
    comparator: float,
    message: str,
) -> None:
    first, second = observations_for(protocol, (0.1, 0.2))
    bounded = (replace(first, candidate_value=candidate, comparator_value=comparator), second)
    with pytest.raises(PairedEstimationError, match=message):
        estimate_paired(PairedMetricSpec("assignment_rate", 0.0, 1.0), bounded)


def test_metric_spec_rejects_invalid_identity_and_bounds() -> None:
    with pytest.raises(PairedEstimationError, match="identity"):
        PairedMetricSpec(" ")
    with pytest.raises(PairedEstimationError, match="finite"):
        PairedMetricSpec("risk", float("nan"), 1.0)
    with pytest.raises(PairedEstimationError, match="must not exceed"):
        PairedMetricSpec("risk", 2.0, 1.0)


@pytest.mark.parametrize(
    ("probability", "degrees_of_freedom", "message"),
    (
        (0.0, 1, "probability"),
        (1.0, 1, "probability"),
        (float("nan"), 1, "probability"),
        (0.5, 0, "degrees"),
        (0.5, True, "degrees"),
    ),
)
def test_student_t_rejects_invalid_parameters(
    probability: float, degrees_of_freedom: int, message: str
) -> None:
    with pytest.raises(PairedEstimationError, match=message):
        student_t_quantile(probability, degrees_of_freedom)


def test_student_t_cdf_rejects_non_finite_value() -> None:
    with pytest.raises(PairedEstimationError, match="finite"):
        student_t_cdf(float("inf"), 4)
    assert student_t_cdf(0.0, 4) == 0.5
