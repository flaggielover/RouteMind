from __future__ import annotations

from dataclasses import dataclass

from .linalg import Vector


@dataclass(frozen=True, slots=True)
class Trajectory:
    layer: str
    alpha: float
    magnitude: float
    direction_id: str
    seed: int
    states: tuple[Vector, ...]

    def transitions(self) -> tuple[tuple[Vector, Vector], ...]:
        return tuple(zip(self.states[:-1], self.states[1:], strict=True))

    def payload(self) -> dict[str, object]:
        return {
            "layer": self.layer,
            "alpha": self.alpha,
            "magnitude": self.magnitude,
            "direction_id": self.direction_id,
            "seed": self.seed,
            "states": self.states,
        }
