from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest

from routemind_compute.application.research_observability import (
    PolicyObservation,
    PolicyTrace,
    ResearchObservationExporter,
    SwitchCostComponent,
    canonical_digest,
)


def _trace() -> PolicyTrace:
    trace = PolicyTrace()
    config = canonical_digest({"mode": "fixture"})
    trace.record(
        run_id="run-1",
        decision_id="d-1",
        request_id="r-1",
        tick=0,
        selected_policy="nearest",
        policy_version="1.0.0",
        configuration_digest=config,
        deterministic_seed=7,
        scenario_id="scenario-1",
    )
    trace.record(
        run_id="run-1",
        decision_id="d-2",
        request_id="r-2",
        tick=2,
        selected_policy="risk-aware",
        policy_version="1.0.0",
        configuration_digest=config,
        deterministic_seed=7,
        scenario_id="scenario-1",
        switch_reason="risk_pressure",
    )
    trace.record(
        run_id="run-1",
        decision_id="d-3",
        request_id="r-3",
        tick=5,
        selected_policy="nearest",
        policy_version="1.0.0",
        configuration_digest=config,
        deterministic_seed=7,
        scenario_id="scenario-1",
    )
    trace.record(
        run_id="run-1",
        decision_id="d-4",
        request_id="r-4",
        tick=8,
        selected_policy="risk-aware",
        policy_version="1.0.0",
        configuration_digest=config,
        deterministic_seed=7,
        scenario_id="scenario-1",
    )
    return trace


def test_trace_records_no_switch_switch_and_multi_policy_reversals() -> None:
    trace = _trace()
    assert trace.observations[0].previous_policy == trace.observations[0].selected_policy
    assert trace.observations[0].switch_occurred is False
    assert [item.switch_occurred for item in trace.observations] == [False, True, True, True]
    metrics = trace.metrics()
    assert metrics.decision_count == 4
    assert metrics.switch_count == 3
    assert metrics.switch_count <= metrics.decision_count
    assert metrics.reversal_count == 2
    assert metrics.dwell_ticks == (2, 3, 3)
    assert ("nearest", "risk-aware", 2) in metrics.transition_matrix


def test_unavailable_component_is_not_silently_zero_and_fallback_is_explicit() -> None:
    component = SwitchCostComponent("route_delta", "UNAVAILABLE", unit="seconds")
    assert component.value is None
    with pytest.raises(ValueError, match="must not contain a value"):
        SwitchCostComponent("route_delta", "UNAVAILABLE", value=0, unit="seconds")
    trace = PolicyTrace()
    trace.record(
        run_id="run-1",
        decision_id="d-1",
        request_id="r-1",
        tick=1,
        selected_policy="nearest",
        policy_version="1.0.0",
        configuration_digest="a" * 64,
        fallback_state="FALLBACK_USED",
        consequences=(component,),
    )
    assert trace.observations[0].fallback_state == "FALLBACK_USED"


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"name": "", "status": "MEASURED", "value": 1}, "name must not be blank"),
        ({"name": "cost", "status": "UNKNOWN", "value": 1}, "unsupported cost component status"),
        ({"name": "cost", "status": "MEASURED"}, "require a value"),
        ({"name": "cost", "status": "MEASURED", "value": math.nan}, "must be finite"),
        ({"name": "cost", "status": "MEASURED", "value": 1, "unit": " "}, "unit must not be blank"),
    ],
)
def test_component_validation_rejects_ambiguous_values(
    kwargs: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        SwitchCostComponent(**kwargs)  # type: ignore[arg-type]


def test_observation_validation_rejects_inconsistent_or_non_replayable_fields() -> None:
    common: dict[str, Any] = {
        "run_id": "run-1",
        "decision_id": "d-1",
        "request_id": "r-1",
        "tick": 1,
        "previous_policy": "nearest",
        "selected_policy": "risk-aware",
        "switch_occurred": True,
        "switch_reason": "switch",
        "selection_mode": "deterministic",
        "policy_version": "1.0.0",
        "configuration_digest": "a" * 64,
        "deterministic_seed": 1,
        "clock_domain": "SIMULATED",
    }
    with pytest.raises(ValueError, match="must match policy transition"):
        PolicyObservation(**{**common, "switch_occurred": False})
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        PolicyObservation(**{**common, "configuration_digest": "A" * 64})
    with pytest.raises(ValueError, match="semantic keys must be unique"):
        PolicyObservation(**{**common, "semantics": (("state", "OBSERVED"), ("state", "DERIVED"))})
    with pytest.raises(ValueError, match="JSON serializable"):
        PolicyObservation(**{**common, "state": (("bad", object()),)})


def test_trace_window_and_empty_metrics_are_explicit() -> None:
    trace = PolicyTrace()
    empty = trace.metrics()
    assert empty.decision_count == 0
    assert empty.switch_rate == 0.0
    with pytest.raises(ValueError, match="window_ticks must be positive"):
        trace.metrics(window_ticks=0)
    trace = _trace()
    window = trace.metrics(window_ticks=3)
    assert window.decision_count == 2
    assert window.policy_occupancy == (("nearest", 1), ("risk-aware", 1))


def test_replay_digest_is_stable_and_timestamp_independent() -> None:
    first = _trace()
    second = _trace()
    assert first.replay_digest() == second.replay_digest()
    assert first.observations[0].replay_digest == second.observations[0].replay_digest


def test_export_uses_data_root_and_redacts_secret_keys(tmp_path: Path) -> None:
    trace = PolicyTrace()
    trace.record(
        run_id="run-1",
        decision_id="d-1",
        request_id="r-1",
        tick=1,
        selected_policy="nearest",
        policy_version="1.0.0",
        configuration_digest="b" * 64,
        state={"api_key": "do-not-export", "active_order_count": 2},
    )
    exported = ResearchObservationExporter(tmp_path).export(trace.observations)
    assert exported.path == tmp_path / "research-observations" / "policy-observations-v1.jsonl"
    row = json.loads(exported.path.read_text(encoding="utf-8"))
    assert row["state"]["api_key"] == "[REDACTED]"
    assert "do-not-export" not in exported.path.read_text(encoding="utf-8")
    manifest = json.loads(exported.manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "routemind-policy-observation-v1"
    assert manifest["root_policy"] == "ROUTEMIND_DATA_ROOT"


def test_export_requires_external_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ROUTEMIND_DATA_ROOT", raising=False)
    with pytest.raises(ValueError, match="ROUTEMIND_DATA_ROOT"):
        ResearchObservationExporter()
