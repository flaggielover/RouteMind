from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from dataclasses import dataclass, replace
from math import isfinite
from threading import RLock
from typing import Literal

from routemind_compute.application.clock import SIMULATED_CLOCK
from routemind_compute.application.registry import StrategyRegistry
from routemind_compute.application.simulation import (
    CourierState,
    DemandEvent,
    ScenarioKernel,
    ScenarioManifest,
)
from routemind_compute.application.travel import TravelTimeProvider
from routemind_compute.domain.dispatch import GeoPoint

TwinAction = Literal[
    "start",
    "pause",
    "resume",
    "step",
    "reset",
    "speed",
    "scenario",
    "seed",
    "strategy",
]
TwinStatus = Literal["paused", "running", "completed"]


class TwinCommandConflict(ValueError):
    """A command id was reused with a different immutable payload."""


@dataclass(frozen=True, slots=True)
class TwinControlCommand:
    command_id: str
    action: TwinAction
    seconds: float | None = None
    speed: float | None = None
    scenario_id: str | None = None
    seed: int | None = None
    strategy: str | None = None

    def __post_init__(self) -> None:
        if not self.command_id.strip():
            raise ValueError("command_id must not be blank")
        if self.action not in {
            "start",
            "pause",
            "resume",
            "step",
            "reset",
            "speed",
            "scenario",
            "seed",
            "strategy",
        }:
            raise ValueError("unsupported twin control action")
        if self.seconds is not None and (
            not isfinite(self.seconds) or self.seconds < 1 or self.seconds > 3600
        ):
            raise ValueError("step seconds must be between 1 and 3600")
        if self.speed is not None and (
            not isfinite(self.speed) or self.speed < 0.1 or self.speed > 10
        ):
            raise ValueError("speed must be between 0.1 and 10")
        if self.seed is not None and (self.seed < 0 or self.seed > 2_147_483_647):
            raise ValueError("seed must be between 0 and 2147483647")
        if self.scenario_id is not None and not self.scenario_id.strip():
            raise ValueError("scenario_id must not be blank")
        if self.strategy is not None and not self.strategy.strip():
            raise ValueError("strategy must not be blank")
        required_fields = {
            "step": self.seconds,
            "speed": self.speed,
            "scenario": self.scenario_id,
            "seed": self.seed,
            "strategy": self.strategy,
        }
        required = required_fields.get(self.action)
        if self.action in required_fields and required is None:
            raise ValueError(f"{self.action} command requires its value")

    @property
    def signature(self) -> str:
        return json.dumps(
            {
                "action": self.action,
                "seconds": self.seconds,
                "speed": self.speed,
                "scenario_id": self.scenario_id,
                "seed": self.seed,
                "strategy": self.strategy,
            },
            sort_keys=True,
            separators=(",", ":"),
        )


@dataclass(frozen=True, slots=True)
class TwinControlEvent:
    event_id: str
    event_type: str
    simulated_time_seconds: float
    command_id: str
    details: tuple[tuple[str, str], ...] = ()
    clock_domain: Literal["SIMULATED"] = SIMULATED_CLOCK

    def __post_init__(self) -> None:
        if not self.event_id.strip() or not self.event_type.strip():
            raise ValueError("twin event identity must not be blank")
        if not isfinite(self.simulated_time_seconds) or self.simulated_time_seconds < 0:
            raise ValueError("twin event time must be finite and non-negative")
        if not self.command_id.strip():
            raise ValueError("twin event command_id must not be blank")


@dataclass(frozen=True, slots=True)
class TwinControlState:
    scenario_id: str
    seed: int
    strategy: str
    strategy_version: str
    status: TwinStatus
    speed: float
    simulated_time_seconds: float
    tick: int
    generation: int
    event_count: int
    last_command_id: str | None
    replay_digest: str
    clock_domain: Literal["SIMULATED"] = SIMULATED_CLOCK


@dataclass(frozen=True, slots=True)
class TwinControlResult:
    command_id: str | None
    state: TwinControlState
    events: tuple[TwinControlEvent, ...]
    replayed: bool = False


class TwinControlService:
    """Bounded process-local control state for the Python Digital Twin."""

    max_recent_commands = 128
    max_events = 1024
    ticks_per_hour = 60

    def __init__(
        self,
        registry: StrategyRegistry,
        travel_provider: TravelTimeProvider,
        scenario_id: str = "control-default",
        seed: int = 7,
        strategy: str = "nearest",
    ) -> None:
        self.registry = registry
        self.travel_provider = travel_provider
        self._lock = RLock()
        self._commands: OrderedDict[str, tuple[str, TwinControlResult]] = OrderedDict()
        self._scenario_id = scenario_id
        self._seed = seed
        self._strategy = strategy
        self._speed = 1.0
        self._simulated_time_seconds = 0.0
        self._status: TwinStatus = "paused"
        self._generation = 0
        self._last_command_id: str | None = None
        self._events: list[TwinControlEvent] = []
        self._emitted_scenario_event_ids: set[str] = set()
        self._rebuild_scenario()

    def snapshot(self) -> TwinControlResult:
        with self._lock:
            return TwinControlResult(None, self._state(), ())

    def apply(self, command: TwinControlCommand) -> TwinControlResult:
        with self._lock:
            cached = self._commands.get(command.command_id)
            if cached is not None:
                signature, result = cached
                if signature != command.signature:
                    raise TwinCommandConflict("command_id was already used for another payload")
                self._commands.move_to_end(command.command_id)
                return replace(result, replayed=True)

            before = len(self._events)
            self._apply_action(command)
            self._last_command_id = command.command_id
            result = TwinControlResult(
                command.command_id,
                self._state(),
                tuple(self._events[before:]),
            )
            self._commands[command.command_id] = (command.signature, result)
            while len(self._commands) > self.max_recent_commands:
                self._commands.popitem(last=False)
            return result

    def _apply_action(self, command: TwinControlCommand) -> None:
        if command.action == "start":
            self._status = "running"
            self._append_event(command, "simulation.started")
        elif command.action == "pause":
            self._status = "paused"
            self._append_event(command, "simulation.paused")
        elif command.action == "resume":
            self._status = "running"
            self._append_event(command, "simulation.resumed")
        elif command.action == "step":
            self._advance(command)
        elif command.action == "reset":
            self._reset(command, "simulation.reset")
        elif command.action == "speed":
            self._speed = command.speed or self._speed
            self._append_event(command, "simulation.speed_changed", {"speed": self._speed})
        elif command.action == "scenario":
            self._scenario_id = command.scenario_id or self._scenario_id
            self._reset(command, "simulation.scenario_changed")
        elif command.action == "seed":
            self._seed = command.seed if command.seed is not None else self._seed
            self._reset(command, "simulation.seed_changed")
        elif command.action == "strategy":
            strategy = command.strategy or self._strategy
            self._ensure_strategy(strategy)
            self._strategy = strategy
            self._reset(command, "simulation.strategy_changed")

    def _advance(self, command: TwinControlCommand) -> None:
        seconds = (command.seconds or 0.0) * self._speed
        self._simulated_time_seconds += seconds
        for event in self._scenario_events:
            if (
                event.event_id not in self._emitted_scenario_event_ids
                and event.simulated_time_seconds <= self._simulated_time_seconds
            ):
                self._emitted_scenario_event_ids.add(event.event_id)
                self._append_event(
                    command,
                    event.event_type,
                    dict(event.details),
                    event.simulated_time_seconds,
                    event.event_id,
                )
        if self._simulated_time_seconds >= self._scenario_end_seconds:
            self._status = "completed"

    def _reset(self, command: TwinControlCommand, event_type: str) -> None:
        self._ensure_strategy(self._strategy)
        self._simulated_time_seconds = 0.0
        self._status = "paused"
        self._generation += 1
        self._events.clear()
        self._emitted_scenario_event_ids.clear()
        self._rebuild_scenario()
        self._append_event(command, event_type)

    def _append_event(
        self,
        command: TwinControlCommand,
        event_type: str,
        details: dict[str, object] | None = None,
        simulated_time_seconds: float | None = None,
        event_id: str | None = None,
    ) -> None:
        values = tuple(sorted((key, str(value)) for key, value in (details or {}).items()))
        event = TwinControlEvent(
            event_id or f"command:{command.command_id}:{len(self._events)}",
            event_type,
            self._simulated_time_seconds
            if simulated_time_seconds is None
            else simulated_time_seconds,
            command.command_id,
            values,
        )
        self._events.append(event)
        if len(self._events) > self.max_events:
            del self._events[: len(self._events) - self.max_events]

    def _rebuild_scenario(self) -> None:
        self._ensure_strategy(self._strategy)
        manifest = _control_manifest(self._scenario_id, self._seed)
        run = ScenarioKernel(
            self.registry,
            self.travel_provider,
            strategy=self._strategy,
            ticks_per_hour=self.ticks_per_hour,
        ).run(manifest)
        self._scenario_end_seconds = max(60.0, (run.simulated_end_tick + 1) * 60.0)
        self._scenario_events = tuple(
            TwinControlEvent(
                f"scenario:{self._scenario_id}:transition:{transition.request_id}",
                "order.assigned" if transition.to_state == "ASSIGNED" else "order.unassigned",
                transition.tick * 60.0,
                "scenario",
                (
                    ("courier_id", transition.courier_id or ""),
                    ("request_id", transition.request_id),
                    ("replay_digest", run.replay_digest),
                ),
            )
            for transition in run.transitions
        )
        self._strategy_version = next(
            descriptor.version
            for descriptor in self.registry.descriptors()
            if descriptor.name == self._strategy
        )

    def _ensure_strategy(self, strategy: str) -> None:
        if strategy not in self.registry.names():
            raise KeyError(f"unknown dispatch strategy: {strategy}")

    def _state(self) -> TwinControlState:
        payload = {
            "scenario_id": self._scenario_id,
            "seed": self._seed,
            "strategy": self._strategy,
            "strategy_version": self._strategy_version,
            "status": self._status,
            "speed": self._speed,
            "simulated_time_seconds": self._simulated_time_seconds,
            "tick": int(self._simulated_time_seconds // 60),
            "generation": self._generation,
            "event_count": len(self._events),
            "last_command_id": self._last_command_id,
            "events": [
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "simulated_time_seconds": event.simulated_time_seconds,
                    "command_id": event.command_id,
                    "details": event.details,
                    "clock_domain": event.clock_domain,
                }
                for event in self._events
            ],
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return TwinControlState(
            self._scenario_id,
            self._seed,
            self._strategy,
            self._strategy_version,
            self._status,
            self._speed,
            self._simulated_time_seconds,
            int(self._simulated_time_seconds // 60),
            self._generation,
            len(self._events),
            self._last_command_id,
            digest,
            SIMULATED_CLOCK,
        )


def _control_manifest(scenario_id: str, seed: int) -> ScenarioManifest:
    digest = hashlib.sha256(f"{scenario_id}:{seed}".encode()).digest()
    latitude = 31.20 + (digest[0] / 2550)
    longitude = 121.40 + (digest[1] / 2550)
    return ScenarioManifest(
        scenario_id,
        seed,
        (
            DemandEvent(
                f"{scenario_id}:order-1",
                GeoPoint(latitude + 0.001, longitude + 0.001),
                0,
                zone="control",
            ),
            DemandEvent(
                f"{scenario_id}:order-2",
                GeoPoint(latitude + 0.002, longitude + 0.002),
                1,
                zone="control",
            ),
        ),
        (
            CourierState(f"{scenario_id}:courier-1", GeoPoint(latitude, longitude)),
            CourierState(
                f"{scenario_id}:courier-2",
                GeoPoint(latitude + 0.01, longitude + 0.01),
            ),
        ),
        delay_ticks=(0, 1),
        traffic_multiplier=1.0 + (digest[2] / 2550),
    )
