from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.twin_fidelity_protocol import (
    TwinFidelityProtocolError,
    assess_fidelity_support,
    load_twin_fidelity_protocol,
)

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = (
    ROOT / "docs" / "research" / "r3" / "manifests" / "twin" / "r3-333-fidelity-protocol-v1.json"
)


def _payload() -> dict[str, object]:
    parsed: object = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if not isinstance(parsed, Mapping):
        raise AssertionError("fixture must be an object")
    return cast(dict[str, object], parsed)


def _mapping(value: object) -> dict[str, object]:
    return dict(cast(Mapping[str, object], value))


def _mappings(value: object) -> list[dict[str, object]]:
    return [_mapping(item) for item in cast(Sequence[object], value)]


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    unsigned = dict(payload)
    unsigned["protocol_digest"] = canonical_digest(
        {key: value for key, value in unsigned.items() if key != "protocol_digest"}
    )
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(unsigned, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_protocol_freezes_variable_appropriate_metrics_and_support() -> None:
    protocol = load_twin_fidelity_protocol(PROTOCOL)
    assert protocol.protocol_id == "r3-333-twin-fidelity-protocol-v1"
    assert [metric.metric_id for metric in protocol.metrics] == [
        "assignment_rate",
        "scenario_risk_index",
        "dispatch_latency_seconds",
        "fallback_rate",
    ]
    assert [metric.absolute_threshold for metric in protocol.metrics] == [0.05, 0.05, 30.0, 0.02]
    assert protocol.metrics[0].minimum_held_out_records == 100
    assert len(protocol.protocol_digest) == 64
    assert len(protocol.manifest_sha256) == 64


def test_support_gate_returns_insufficient_then_ready_without_estimating_effect() -> None:
    protocol = load_twin_fidelity_protocol(PROTOCOL)
    missing = assess_fidelity_support(protocol, {})
    assert missing.status == "INSUFFICIENT_DATA"
    assert missing.missing_metrics == tuple(metric.metric_id for metric in protocol.metrics)
    ready = assess_fidelity_support(
        protocol, {metric.metric_id: 100 for metric in protocol.metrics}
    )
    assert ready.status == "READY_FOR_VALIDATION"
    assert ready.missing_metrics == ()
    assert ready.claim_boundary == "FIDELITY_PROTOCOL_DOES_NOT_ESTABLISH_TWIN_VALIDITY"


def test_protocol_rejects_forged_digest_and_non_object_json(tmp_path: Path) -> None:
    payload = _payload()
    payload["question"] = "changed"
    forged = tmp_path / "forged.json"
    forged.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(TwinFidelityProtocolError, match="digest"):
        load_twin_fidelity_protocol(forged)

    scalar = tmp_path / "scalar.json"
    scalar.write_text("[]", encoding="utf-8")
    with pytest.raises(TwinFidelityProtocolError, match="JSON object"):
        load_twin_fidelity_protocol(scalar)

    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b"not-json")
    with pytest.raises(TwinFidelityProtocolError, match="UTF-8 JSON"):
        load_twin_fidelity_protocol(invalid)


def test_protocol_rejects_root_identity_and_claim_boundary_drift(tmp_path: Path) -> None:
    payload = _payload()
    del payload["question"]
    with pytest.raises(TwinFidelityProtocolError, match="fields mismatch"):
        load_twin_fidelity_protocol(_write(tmp_path, payload))

    payload = _payload()
    payload["task_id"] = "R3-330"
    with pytest.raises(TwinFidelityProtocolError, match="identity"):
        load_twin_fidelity_protocol(_write(tmp_path, payload))

    payload = _payload()
    payload["claim_boundary"] = "other"
    with pytest.raises(TwinFidelityProtocolError, match="claim boundary"):
        load_twin_fidelity_protocol(_write(tmp_path, payload))


def test_protocol_rejects_support_policy_drift(tmp_path: Path) -> None:
    payload = _payload()
    support = _mapping(payload["support_policy"])
    support["minimum_held_out_records"] = 0
    payload["support_policy"] = support
    with pytest.raises(TwinFidelityProtocolError, match="positive"):
        load_twin_fidelity_protocol(_write(tmp_path, payload))

    payload = _payload()
    support = _mapping(payload["support_policy"])
    support["status_when_missing"] = "PASS"
    payload["support_policy"] = support
    with pytest.raises(TwinFidelityProtocolError, match="INSUFFICIENT_DATA"):
        load_twin_fidelity_protocol(_write(tmp_path, payload))

    payload = _payload()
    support = _mapping(payload["support_policy"])
    support["unexpected"] = True
    payload["support_policy"] = support
    with pytest.raises(TwinFidelityProtocolError, match="fields mismatch"):
        load_twin_fidelity_protocol(_write(tmp_path, payload))


def test_protocol_rejects_improvement_policy_drift(tmp_path: Path) -> None:
    payload = _payload()
    policy = _mapping(payload["improvement_policy"])
    policy["comparison"] = "other"
    payload["improvement_policy"] = policy
    with pytest.raises(TwinFidelityProtocolError, match="baseline"):
        load_twin_fidelity_protocol(_write(tmp_path, payload))

    payload = _payload()
    policy = _mapping(payload["improvement_policy"])
    policy["confidence_level"] = 1.0
    payload["improvement_policy"] = policy
    with pytest.raises(TwinFidelityProtocolError, match="between"):
        load_twin_fidelity_protocol(_write(tmp_path, payload))

    payload = _payload()
    policy = _mapping(payload["improvement_policy"])
    policy["required_before_validation"] = False
    payload["improvement_policy"] = policy
    with pytest.raises(TwinFidelityProtocolError, match="fixed"):
        load_twin_fidelity_protocol(_write(tmp_path, payload))


def test_protocol_rejects_metric_count_order_and_shape(tmp_path: Path) -> None:
    payload = _payload()
    payload["metrics"] = _mappings(payload["metrics"])[:3]
    with pytest.raises(TwinFidelityProtocolError, match="exactly four"):
        load_twin_fidelity_protocol(_write(tmp_path, payload))

    payload = _payload()
    metrics = _mappings(payload["metrics"])
    metrics.reverse()
    payload["metrics"] = metrics
    with pytest.raises(TwinFidelityProtocolError, match="identity/order"):
        load_twin_fidelity_protocol(_write(tmp_path, payload))

    payload = _payload()
    metrics = _mappings(payload["metrics"])
    del metrics[0]["unit"]
    payload["metrics"] = metrics
    with pytest.raises(TwinFidelityProtocolError, match="fields mismatch"):
        load_twin_fidelity_protocol(_write(tmp_path, payload))


def test_protocol_rejects_metric_identity_threshold_and_support_drift(tmp_path: Path) -> None:
    payload = _payload()
    metrics = _mappings(payload["metrics"])
    metrics[0]["metric_id"] = "other"
    payload["metrics"] = metrics
    with pytest.raises(TwinFidelityProtocolError, match="identity"):
        load_twin_fidelity_protocol(_write(tmp_path, payload))

    payload = _payload()
    metrics = _mappings(payload["metrics"])
    metrics[0]["absolute_threshold"] = -1.0
    payload["metrics"] = metrics
    with pytest.raises(TwinFidelityProtocolError, match="thresholds"):
        load_twin_fidelity_protocol(_write(tmp_path, payload))

    payload = _payload()
    metrics = _mappings(payload["metrics"])
    metrics[0]["minimum_held_out_records"] = 101
    payload["metrics"] = metrics
    with pytest.raises(TwinFidelityProtocolError, match="support counts"):
        load_twin_fidelity_protocol(_write(tmp_path, payload))


def test_protocol_rejects_metric_alpha_effect_and_non_finite_values(tmp_path: Path) -> None:
    payload = _payload()
    metrics = _mappings(payload["metrics"])
    metrics[0]["improvement_alpha"] = 0.1
    payload["metrics"] = metrics
    with pytest.raises(TwinFidelityProtocolError, match="alpha"):
        load_twin_fidelity_protocol(_write(tmp_path, payload))

    payload = _payload()
    metrics = _mappings(payload["metrics"])
    metrics[0]["improvement_effect"] = -0.1
    payload["metrics"] = metrics
    with pytest.raises(TwinFidelityProtocolError, match="thresholds"):
        load_twin_fidelity_protocol(_write(tmp_path, payload))

    payload = _payload()
    metrics = _mappings(payload["metrics"])
    metrics[0]["absolute_threshold"] = float("nan")
    with pytest.raises(ValueError):
        _write(tmp_path, {**payload, "metrics": metrics})


def test_support_gate_rejects_invalid_counts() -> None:
    protocol = load_twin_fidelity_protocol(PROTOCOL)
    with pytest.raises(TwinFidelityProtocolError, match="count is invalid"):
        assess_fidelity_support(protocol, {"assignment_rate": -1})
    with pytest.raises(TwinFidelityProtocolError, match="count is invalid"):
        assess_fidelity_support(protocol, {"assignment_rate": True})


def test_protocol_rejects_scalar_mapping_sequence_text_number_integer_and_bool(
    tmp_path: Path,
) -> None:
    payload = _payload()
    payload["support_policy"] = "invalid"
    with pytest.raises(TwinFidelityProtocolError, match="object"):
        load_twin_fidelity_protocol(_write(tmp_path, payload))

    payload = _payload()
    payload["metrics"] = "invalid"
    with pytest.raises(TwinFidelityProtocolError, match="array"):
        load_twin_fidelity_protocol(_write(tmp_path, payload))

    payload = _payload()
    payload["question"] = ""
    with pytest.raises(TwinFidelityProtocolError, match="non-empty text"):
        load_twin_fidelity_protocol(_write(tmp_path, payload))

    payload = _payload()
    policy = _mapping(payload["improvement_policy"])
    policy["confidence_level"] = True
    payload["improvement_policy"] = policy
    with pytest.raises(TwinFidelityProtocolError, match="finite number"):
        load_twin_fidelity_protocol(_write(tmp_path, payload))

    payload = _payload()
    support = _mapping(payload["support_policy"])
    support["minimum_calibration_records"] = True
    payload["support_policy"] = support
    with pytest.raises(TwinFidelityProtocolError, match="integer"):
        load_twin_fidelity_protocol(_write(tmp_path, payload))

    payload = _payload()
    policy = _mapping(payload["improvement_policy"])
    policy["required_before_validation"] = "yes"
    payload["improvement_policy"] = policy
    with pytest.raises(TwinFidelityProtocolError, match="boolean"):
        load_twin_fidelity_protocol(_write(tmp_path, payload))


def test_protocol_file_digest_is_stable() -> None:
    first = load_twin_fidelity_protocol(PROTOCOL)
    second = load_twin_fidelity_protocol(PROTOCOL)
    assert first.manifest_sha256 == second.manifest_sha256
    assert first.manifest_sha256 == sha256(PROTOCOL.read_bytes()).hexdigest()
