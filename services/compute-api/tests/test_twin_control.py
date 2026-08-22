from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from routemind_compute.api.app import app
from routemind_compute.application.baselines import WeightedGreedyStrategy
from routemind_compute.application.nearest import NearestStrategy
from routemind_compute.application.registry import default_registry
from routemind_compute.application.simulation import ScenarioKernel
from routemind_compute.application.travel import DeterministicLocalTravelProvider
from routemind_compute.application.twin_control import (
    TwinCommandConflict,
    TwinControlCommand,
    TwinControlEvent,
    TwinControlResult,
    TwinControlService,
)

client = TestClient(app)


def service() -> TwinControlService:
    return TwinControlService(default_registry(), DeterministicLocalTravelProvider())


def apply(
    service: TwinControlService, command_id: str, action: str, **kwargs: object
) -> TwinControlResult:
    return service.apply(TwinControlCommand(command_id, action, **kwargs))  # type: ignore[arg-type]


def test_control_commands_are_bounded_and_emit_replayable_state() -> None:
    twin = service()
    assert twin.snapshot().state.status == "paused"
    started = apply(twin, "start-1", "start")
    assert started.state.status == "running"
    assert started.events[0].event_type == "simulation.started"
    replay = apply(twin, "start-1", "start")
    assert replay.replayed is True
    assert replay.events == started.events

    assert apply(twin, "pause-1", "pause").state.status == "paused"
    assert apply(twin, "resume-1", "resume").state.status == "running"
    speed = apply(twin, "speed-1", "speed", speed=2.0)
    assert speed.state.speed == 2.0
    stepped = apply(twin, "step-1", "step", seconds=30.0)
    assert stepped.state.simulated_time_seconds == 60.0
    assert stepped.state.event_count >= 2
    completed = apply(twin, "step-2", "step", seconds=120.0)
    assert completed.state.status == "completed"
    assert completed.state.replay_digest == twin.snapshot().state.replay_digest

    reset = apply(twin, "reset-1", "reset")
    assert reset.state.status == "paused"
    assert reset.state.simulated_time_seconds == 0
    assert reset.state.generation == 1
    scenario = apply(twin, "scenario-1", "scenario", scenario_id="new-scenario")
    assert scenario.state.scenario_id == "new-scenario"
    seeded = apply(twin, "seed-1", "seed", seed=0)
    assert seeded.state.seed == 0
    changed = apply(twin, "strategy-1", "strategy", strategy="weighted-greedy")
    assert changed.state.strategy == "weighted-greedy"
    assert changed.state.strategy_version == "1.0.0"


def test_control_replay_and_validation_contracts() -> None:
    twin = service()
    apply(twin, "same", "speed", speed=1.0)
    with pytest.raises(TwinCommandConflict, match="another payload"):
        apply(twin, "same", "speed", speed=2.0)
    with pytest.raises(KeyError, match="unknown dispatch strategy"):
        apply(twin, "unknown", "strategy", strategy="missing")
    with pytest.raises(ValueError, match="requires"):
        TwinControlCommand("missing", "step")
    with pytest.raises(ValueError, match="between 1 and 3600"):
        TwinControlCommand("bad-step", "step", seconds=0)
    with pytest.raises(ValueError, match=r"between 0\.1 and 10"):
        TwinControlCommand("bad-speed", "speed", speed=11)
    with pytest.raises(ValueError, match="seed"):
        TwinControlCommand("bad-seed", "seed", seed=-1)
    with pytest.raises(ValueError, match="scenario_id"):
        TwinControlCommand("bad-scenario", "scenario", scenario_id=" ")
    with pytest.raises(ValueError, match="strategy"):
        TwinControlCommand("bad-strategy", "strategy", strategy=" ")
    with pytest.raises(ValueError, match="unsupported"):
        TwinControlCommand("bad-action", "other")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="event identity"):
        TwinControlEvent(" ", "event", 0, "command")
    with pytest.raises(ValueError, match="event time"):
        TwinControlEvent("event", "event", -1, "command")
    with pytest.raises(ValueError, match="command_id"):
        TwinControlEvent("event", "event", 0, " ")


def test_control_history_bounds_and_deterministic_manifest() -> None:
    first = service()
    second = service()
    first.max_recent_commands = 1
    apply(first, "one", "start")
    apply(first, "two", "pause")
    assert apply(first, "one", "start").replayed is False
    first.max_events = 1
    apply(first, "three", "resume")
    assert first.snapshot().state.event_count == 1

    apply(second, "one", "start")
    assert first.snapshot().state.replay_digest != second.snapshot().state.replay_digest
    assert ScenarioKernel is not None
    assert NearestStrategy().name == "nearest"
    assert WeightedGreedyStrategy().name == "weighted-greedy"


def test_twin_control_http_api_exposes_state_events_and_failures() -> None:
    reset = client.post(
        "/api/v1/twin/control",
        json={"command_id": "api-reset", "action": "reset"},
    )
    assert reset.status_code == 200
    assert reset.json()["source"] == "simulation"
    assert reset.json()["state"]["status"] == "paused"

    state = client.get("/api/v1/twin/state")
    assert state.status_code == 200
    assert state.json()["replay_digest"]
    stepped = client.post(
        "/api/v1/twin/control",
        json={"command_id": "api-step", "action": "step", "seconds": 60},
    )
    assert stepped.status_code == 200
    assert stepped.json()["state"]["simulated_time_seconds"] == 60
    replayed = client.post(
        "/api/v1/twin/control",
        json={"command_id": "api-step", "action": "step", "seconds": 60},
    )
    assert replayed.status_code == 200
    assert replayed.json()["replayed"] is True
    conflict = client.post(
        "/api/v1/twin/control",
        json={"command_id": "api-step", "action": "step", "seconds": 61},
    )
    assert conflict.status_code == 409
    unknown = client.post(
        "/api/v1/twin/control",
        json={"command_id": "api-unknown", "action": "strategy", "strategy": "missing"},
    )
    assert unknown.status_code == 400
    invalid = client.post(
        "/api/v1/twin/control",
        json={"command_id": "api-invalid", "action": "step"},
    )
    assert invalid.status_code == 422
