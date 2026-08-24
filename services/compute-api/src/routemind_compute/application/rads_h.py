"""Formal, deterministic RADS-H hysteresis state transitions for R3-341."""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import isfinite
from typing import Literal

Action = Literal["switch", "hold"]


def _text(value: str, name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must not be blank")
    if len(normalized) > 256:
        raise ValueError(f"{name} exceeds 256 characters")
    return normalized


@dataclass(frozen=True, slots=True)
class RadsHConfig:
    """Frozen hysteresis parameters; values are policy inputs, not results."""

    enter_threshold: float = 0.05
    exit_threshold: float = 0.02
    persistence_ticks: int = 2
    minimum_dwell_ticks: int = 3
    switching_cost: float = 0.01

    def __post_init__(self) -> None:
        if not isfinite(self.enter_threshold) or self.enter_threshold <= 0:
            raise ValueError("enter_threshold must be finite and positive")
        if not isfinite(self.exit_threshold) or self.exit_threshold < 0:
            raise ValueError("exit_threshold must be finite and non-negative")
        if self.exit_threshold >= self.enter_threshold:
            raise ValueError("exit_threshold must be below enter_threshold")
        if (
            isinstance(self.persistence_ticks, bool)
            or not isinstance(self.persistence_ticks, int)
            or self.persistence_ticks <= 0
        ):
            raise ValueError("persistence_ticks must be a positive integer")
        if (
            isinstance(self.minimum_dwell_ticks, bool)
            or not isinstance(self.minimum_dwell_ticks, int)
            or self.minimum_dwell_ticks < 0
        ):
            raise ValueError("minimum_dwell_ticks must be a non-negative integer")
        if not isfinite(self.switching_cost) or self.switching_cost < 0:
            raise ValueError("switching_cost must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class RadsHState:
    active_strategy: str
    regime_id: str
    pressure_ticks: int = 0
    dwell_ticks: int = 0
    switch_count: int = 0

    def __post_init__(self) -> None:
        _text(self.active_strategy, "active_strategy")
        _text(self.regime_id, "regime_id")
        for value, name, minimum in (
            (self.pressure_ticks, "pressure_ticks", 0),
            (self.dwell_ticks, "dwell_ticks", 0),
            (self.switch_count, "switch_count", 0),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise ValueError(f"{name} must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class RadsHDecision:
    action: Action
    reason: str
    previous_strategy: str
    selected_strategy: str
    regime_id: str
    relative_advantage: float
    applied_switching_cost: float
    next_state: RadsHState

    def __post_init__(self) -> None:
        if self.action not in {"switch", "hold"}:
            raise ValueError("RADS-H action is unsupported")
        _text(self.reason, "reason")
        _text(self.previous_strategy, "previous_strategy")
        _text(self.selected_strategy, "selected_strategy")
        _text(self.regime_id, "regime_id")
        if not isfinite(self.relative_advantage):
            raise ValueError("relative_advantage must be finite")
        if not isfinite(self.applied_switching_cost) or self.applied_switching_cost < 0:
            raise ValueError("applied_switching_cost must be finite and non-negative")


def evaluate_rads_h(
    config: RadsHConfig,
    state: RadsHState,
    *,
    candidate_strategy: str,
    candidate_score: float,
    current_score: float,
    regime_id: str,
) -> RadsHDecision:
    """Evaluate one bounded pressure tick and return a new immutable state."""

    candidate = _text(candidate_strategy, "candidate_strategy")
    regime = _text(regime_id, "regime_id")
    if not isfinite(candidate_score) or not isfinite(current_score):
        raise ValueError("RADS-H objective scores must be finite")
    previous = state.active_strategy
    if state.regime_id != regime:
        next_state = replace(state, regime_id=regime, pressure_ticks=0, dwell_ticks=0)
        return _decision("hold", "regime-reset", previous, candidate, regime, 0.0, 0.0, next_state)
    if candidate == previous:
        next_state = replace(state, pressure_ticks=0, dwell_ticks=state.dwell_ticks + 1)
        return _decision(
            "hold", "active-strategy", previous, candidate, regime, 0.0, 0.0, next_state
        )
    denominator = max(abs(current_score), 1e-12)
    advantage = (current_score - candidate_score) / denominator
    if state.dwell_ticks < config.minimum_dwell_ticks:
        next_state = replace(state, pressure_ticks=0, dwell_ticks=state.dwell_ticks + 1)
        return _decision(
            "hold", "minimum-dwell", previous, candidate, regime, advantage, 0.0, next_state
        )
    if advantage < -config.exit_threshold:
        next_state = replace(state, pressure_ticks=0, dwell_ticks=state.dwell_ticks + 1)
        return _decision(
            "hold", "outside-exit-band", previous, candidate, regime, advantage, 0.0, next_state
        )
    if advantage < config.enter_threshold:
        next_state = replace(state, pressure_ticks=0, dwell_ticks=state.dwell_ticks + 1)
        return _decision(
            "hold", "below-enter-threshold", previous, candidate, regime, advantage, 0.0, next_state
        )
    pressure = state.pressure_ticks + 1
    if pressure < config.persistence_ticks:
        next_state = replace(state, pressure_ticks=pressure, dwell_ticks=state.dwell_ticks + 1)
        return _decision(
            "hold", "persistence-required", previous, candidate, regime, advantage, 0.0, next_state
        )
    next_state = RadsHState(
        candidate, regime, pressure_ticks=0, dwell_ticks=0, switch_count=state.switch_count + 1
    )
    return _decision(
        "switch",
        "persistence-satisfied",
        previous,
        candidate,
        regime,
        advantage,
        config.switching_cost,
        next_state,
    )


def _decision(
    action: Action,
    reason: str,
    previous: str,
    selected: str,
    regime: str,
    advantage: float,
    cost: float,
    next_state: RadsHState,
) -> RadsHDecision:
    return RadsHDecision(action, reason, previous, selected, regime, advantage, cost, next_state)


__all__ = ["RadsHConfig", "RadsHDecision", "RadsHState", "evaluate_rads_h"]
