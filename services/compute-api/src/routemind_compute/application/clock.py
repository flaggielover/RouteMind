from __future__ import annotations

from typing import Literal

ClockDomain = Literal["WALL", "SIMULATED", "REPLAY"]

WALL_CLOCK: ClockDomain = "WALL"
SIMULATED_CLOCK: Literal["SIMULATED"] = "SIMULATED"
REPLAY_CLOCK: Literal["REPLAY"] = "REPLAY"


def validate_clock_domain(domain: ClockDomain, *, allowed: tuple[ClockDomain, ...]) -> None:
    if domain not in allowed:
        values = ", ".join(allowed)
        raise ValueError(f"clock domain must be one of: {values}")
