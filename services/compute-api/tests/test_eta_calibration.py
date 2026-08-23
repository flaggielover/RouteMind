import pytest

from routemind_compute.application.eta_calibration import (
    EtaCalibrationSample,
    calibrate,
    classify_sla_risk,
)


def sample(sample_id: str, predicted: float, actual: float) -> EtaCalibrationSample:
    return EtaCalibrationSample(sample_id, predicted, actual, predicted - 10, predicted + 10)


def test_calibration_reports_error_metrics_and_interval_coverage() -> None:
    result = calibrate((sample("a", 100, 110), sample("b", 120, 100), sample("c", 90, 90)))

    assert result.status == "AVAILABLE"
    assert result.sample_count == 3
    assert result.mae_seconds == pytest.approx(10)
    assert result.median_error_seconds == pytest.approx(10)
    assert result.p90_error_seconds == pytest.approx(18)
    assert result.interval_coverage == pytest.approx(2 / 3)
    assert len(result.digest) == 64


def test_calibration_is_unavailable_without_outcomes_and_risk_is_explicit() -> None:
    calibration = calibrate(())
    on_track = classify_sla_risk(80, 100, calibration)
    at_risk = classify_sla_risk(95, 100, calibration)
    late = classify_sla_risk(101, 100, calibration)

    assert calibration.status == "UNAVAILABLE"
    assert calibration.mae_seconds is None
    assert on_track.status == "ON_TRACK"
    assert at_risk.status == "AT_RISK"
    assert late.status == "LIKELY_LATE"
    assert on_track.customer_confidence == "unavailable"


def test_calibration_validates_duplicates_bounds_and_sla() -> None:
    with pytest.raises(ValueError, match="unique"):
        calibrate((sample("same", 10, 10), sample("same", 20, 20)))
    with pytest.raises(ValueError, match="both bounds"):
        EtaCalibrationSample("bad", 1, 1, 0, None)
    with pytest.raises(ValueError, match="lower bound"):
        EtaCalibrationSample("bad", 1, 1, 3, 2)
    with pytest.raises(ValueError, match="SLA"):
        classify_sla_risk(1, 0, calibrate(()))
