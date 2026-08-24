from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from routemind_compute.application.statistical_routebench_multiplicity import (
    ConfirmatoryHypothesisTest,
    MultiplicityControlError,
    PrimaryMetricId,
    apply_frozen_holm_family,
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
METRICS = ("scenario_risk_index", "assignment_rate")


@pytest.fixture(scope="module")
def protocol() -> StatisticalRouteBenchProtocol:
    return load_statistical_routebench_protocol(PROTOCOL_PATH)


def family(
    protocol: StatisticalRouteBenchProtocol,
    raw_p_values: tuple[float, ...] | None = None,
) -> tuple[ConfirmatoryHypothesisTest, ...]:
    values = raw_p_values or (0.001,) * protocol.number_of_confirmatory_tests
    identities = tuple(
        (regime_id, metric_id) for metric_id in METRICS for regime_id in protocol.regime_ids
    )
    return tuple(
        ConfirmatoryHypothesisTest(protocol.protocol_id, regime_id, metric_id, raw_p_value)  # type: ignore[arg-type]
        for (regime_id, metric_id), raw_p_value in zip(identities, values, strict=True)
    )


def test_holm_report_preserves_frozen_identity_and_raw_values(
    protocol: StatisticalRouteBenchProtocol,
) -> None:
    source = family(protocol)
    report = apply_frozen_holm_family(protocol, tuple(reversed(source)))

    assert report.protocol_id == protocol.protocol_id
    assert report.method == "holm_bonferroni_familywise"
    assert report.family == "eight_risk_superiority_and_eight_assignment_noninferiority_tests"
    assert report.familywise_alpha == pytest.approx(0.05)
    assert report.family_size == 16
    assert tuple((item.regime_id, item.metric_id) for item in report.tests) == tuple(
        (regime_id, metric_id) for metric_id in METRICS for regime_id in protocol.regime_ids
    )
    assert tuple(item.raw_p_value for item in report.tests) == (0.001,) * 16
    assert tuple(item.family_rank for item in report.tests) == tuple(range(1, 17))
    assert all(item.adjusted_p_value == pytest.approx(0.016) for item in report.tests)
    assert all(item.rejected for item in report.tests)
    assert report.rejected_count == 16
    assert report.all_rejected
    assert report.disposition == "ALL_CONFIRMATORY_TESTS_REJECTED"
    assert report.claim_boundary == "MULTIPLICITY_ACCOUNTING_NOT_EFFECT_CLAIM"


def test_holm_reference_vector_is_monotonic_and_stops_after_failure(
    protocol: StatisticalRouteBenchProtocol,
) -> None:
    raw = (0.001, 0.002, 0.003, 0.004, *(1.0,) * 12)
    report = apply_frozen_holm_family(protocol, family(protocol, raw))
    ranked = sorted(report.tests, key=lambda item: item.family_rank)

    assert tuple(item.adjusted_p_value for item in ranked[:4]) == pytest.approx(
        (0.016, 0.030, 0.042, 0.052)
    )
    assert tuple(item.holm_multiplier for item in ranked[:4]) == (16, 15, 14, 13)
    assert tuple(item.rejected for item in ranked[:4]) == (True, True, True, False)
    assert all(not item.rejected for item in ranked[3:])
    assert tuple(item.adjusted_p_value for item in ranked) == tuple(
        sorted(item.adjusted_p_value for item in ranked)
    )
    assert report.rejected_count == 3
    assert not report.all_rejected
    assert report.disposition == "ONE_OR_MORE_CONFIRMATORY_TESTS_NOT_REJECTED"


def test_holm_boundary_and_ties_are_deterministic(
    protocol: StatisticalRouteBenchProtocol,
) -> None:
    report = apply_frozen_holm_family(protocol, family(protocol, (0.003125,) * 16))

    assert tuple(item.family_rank for item in report.tests) == tuple(range(1, 17))
    assert all(item.adjusted_p_value == pytest.approx(0.05) for item in report.tests)
    assert all(item.rejected for item in report.tests)


def test_report_digest_is_order_invariant_and_value_sensitive(
    protocol: StatisticalRouteBenchProtocol,
) -> None:
    source = family(protocol)
    forward = apply_frozen_holm_family(protocol, source)
    reverse = apply_frozen_holm_family(protocol, tuple(reversed(source)))
    changed_source = (replace(source[0], raw_p_value=0.1), *source[1:])
    changed = apply_frozen_holm_family(protocol, changed_source)

    assert forward == reverse
    assert forward.report_digest == reverse.report_digest
    assert len(forward.report_digest) == 64
    assert changed.report_digest != forward.report_digest
    assert not changed.all_rejected


def test_hypothesis_payload_retains_identity(protocol: StatisticalRouteBenchProtocol) -> None:
    item = family(protocol)[0]

    assert item.hypothesis_id == (f"{protocol.protocol_id}:normal:scenario_risk_index")
    assert item.payload() == {
        "hypothesis_id": item.hypothesis_id,
        "protocol_id": protocol.protocol_id,
        "regime_id": "normal",
        "metric_id": "scenario_risk_index",
        "raw_p_value": 0.001,
    }


@pytest.mark.parametrize("raw_p_value", (-0.1, 1.1, float("nan"), float("inf"), True))
def test_hypothesis_rejects_invalid_raw_p_values(
    protocol: StatisticalRouteBenchProtocol, raw_p_value: float
) -> None:
    with pytest.raises(MultiplicityControlError, match="raw p-value"):
        ConfirmatoryHypothesisTest(
            protocol.protocol_id,
            "normal",
            "scenario_risk_index",
            raw_p_value,
        )


@pytest.mark.parametrize(
    ("protocol_id", "regime_id", "metric_id", "message"),
    (
        (" ", "normal", "scenario_risk_index", "identities"),
        ("protocol", " ", "scenario_risk_index", "identities"),
        ("protocol", "normal", "runtime_millis", "primary metric"),
    ),
)
def test_hypothesis_rejects_invalid_identity(
    protocol_id: str, regime_id: str, metric_id: str, message: str
) -> None:
    with pytest.raises(MultiplicityControlError, match=message):
        ConfirmatoryHypothesisTest(protocol_id, regime_id, cast(PrimaryMetricId, metric_id), 0.01)


def test_family_rejects_protocol_identity_drift(
    protocol: StatisticalRouteBenchProtocol,
) -> None:
    source = family(protocol)
    drifted = (replace(source[0], protocol_id="other"), *source[1:])

    with pytest.raises(MultiplicityControlError, match="protocol identity"):
        apply_frozen_holm_family(protocol, drifted)


def test_family_rejects_duplicate_and_incomplete_identities(
    protocol: StatisticalRouteBenchProtocol,
) -> None:
    source = family(protocol)
    duplicate = (source[1], *source[1:])
    with pytest.raises(MultiplicityControlError, match="duplicate"):
        apply_frozen_holm_family(protocol, duplicate)

    with pytest.raises(MultiplicityControlError, match="every frozen hypothesis"):
        apply_frozen_holm_family(protocol, source[:-1])


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("multiplicity_method", "bonferroni", "method"),
        ("multiplicity_family", "other", "family description"),
        ("number_of_confirmatory_tests", 8, "test count"),
        ("regime_ids", "duplicate", "identities must be unique"),
        ("familywise_alpha", 0.0, "familywise alpha"),
        ("familywise_alpha", float("nan"), "familywise alpha"),
        ("familywise_alpha", True, "familywise alpha"),
    ),
)
def test_family_rejects_frozen_protocol_drift(
    protocol: StatisticalRouteBenchProtocol, field: str, value: object, message: str
) -> None:
    if field == "multiplicity_method":
        drifted = replace(protocol, multiplicity_method=str(value))
    elif field == "multiplicity_family":
        drifted = replace(protocol, multiplicity_family=str(value))
    elif field == "number_of_confirmatory_tests":
        if not isinstance(value, int) or isinstance(value, bool):
            raise AssertionError("test fixture count must be an integer")
        drifted = replace(protocol, number_of_confirmatory_tests=value)
    elif field == "regime_ids":
        drifted = replace(
            protocol,
            regime_ids=(*protocol.regime_ids[:-1], protocol.regime_ids[0]),
        )
    else:
        drifted = replace(protocol, familywise_alpha=value)  # type: ignore[arg-type]

    with pytest.raises(MultiplicityControlError, match=message):
        apply_frozen_holm_family(drifted, family(protocol))
