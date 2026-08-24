from __future__ import annotations

from math import atan, exp, pi, tanh

from .reason_codes import fail


def evaluate(name: str, value: float) -> float:
    if name == "tanh":
        return tanh(value)
    if name == "logistic":
        if value >= 0:
            decay = exp(-value)
            return 4.0 * (1.0 / (1.0 + decay) - 0.5)
        growth = exp(value)
        return 4.0 * (growth / (1.0 + growth) - 0.5)
    if name == "clipped_linear":
        return max(-1.0, min(1.0, value))
    if name == "atan":
        return 2.0 * atan((pi / 2.0) * value) / pi
    fail("UNKNOWN_NONLINEARITY", name)
