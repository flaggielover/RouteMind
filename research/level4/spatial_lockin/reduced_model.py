from __future__ import annotations

import random
from dataclasses import dataclass

from .linalg import (
    Matrix,
    Vector,
    add_vector,
    dot,
    matrix,
    matvec,
    outer,
    scale_vector,
    vector,
)
from .nonlinearities import evaluate
from .records import Trajectory


@dataclass(frozen=True, slots=True)
class ReducedModel:
    a: Matrix
    b: Vector
    c: Vector
    nonlinearity: str
    version: str

    @classmethod
    def from_config(cls, payload: dict[str, object]) -> ReducedModel:
        return cls(
            matrix(payload["a"]),
            vector(payload["b"]),
            vector(payload["c"]),
            str(payload["nonlinearity"]),
            str(payload["model_version"]),
        )

    @property
    def m(self) -> Matrix:
        return outer(self.b, self.c)

    def step(
        self, state: Vector, alpha: float, *, rng: random.Random, noise_sd: float
    ) -> Vector:
        feedback = scale_vector(
            self.b, alpha * evaluate(self.nonlinearity, dot(self.c, state))
        )
        noise: Vector = tuple(rng.gauss(0.0, noise_sd) for _ in range(3))  # type: ignore[assignment]
        return add_vector(add_vector(matvec(self.a, state), feedback), noise)

    def simulate(
        self,
        initial: Vector,
        alpha: float,
        horizon: int,
        seed: int,
        noise_sd: float,
        *,
        magnitude: float,
        direction_id: str,
    ) -> Trajectory:
        rng = random.Random(seed)
        states = [initial]
        for _ in range(horizon):
            states.append(self.step(states[-1], alpha, rng=rng, noise_sd=noise_sd))
        return Trajectory("R", alpha, magnitude, direction_id, seed, tuple(states))
