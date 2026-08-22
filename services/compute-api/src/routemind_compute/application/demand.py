from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from math import isfinite

from routemind_compute.application.simulation import DemandEvent
from routemind_compute.domain.dispatch import GeoPoint


@dataclass(frozen=True, slots=True)
class DemandArrivalProfile:
    profile_id: str
    rate_per_hour: float
    start_tick: int
    end_tick: int
    location: GeoPoint
    zone: str = ""
    merchant_id: str = ""
    order_profile: str = "standard"
    burst_size: int = 1

    def __post_init__(self) -> None:
        if not self.profile_id.strip():
            raise ValueError("demand profile id must not be blank")
        if not isfinite(self.rate_per_hour) or self.rate_per_hour < 0:
            raise ValueError("demand rate must be finite and non-negative")
        if self.start_tick < 0 or self.end_tick < self.start_tick:
            raise ValueError("demand profile ticks must be ordered and non-negative")
        if not self.order_profile.strip():
            raise ValueError("order profile must not be blank")
        if self.burst_size <= 0:
            raise ValueError("burst size must be positive")


@dataclass(frozen=True, slots=True)
class DemandArrivalRun:
    seed: int
    profiles: tuple[DemandArrivalProfile, ...]
    arrivals: tuple[DemandEvent, ...]
    replay_digest: str


class DemandArrivalGenerator:
    """Generate bounded, seeded arrivals with explicit profile provenance."""

    def __init__(self, ticks_per_hour: int = 60) -> None:
        if ticks_per_hour <= 0:
            raise ValueError("ticks_per_hour must be positive")
        self.ticks_per_hour = ticks_per_hour

    def generate(self, profiles: tuple[DemandArrivalProfile, ...], seed: int) -> DemandArrivalRun:
        if len({profile.profile_id for profile in profiles}) != len(profiles):
            raise ValueError("demand profile identifiers must be unique")
        rng = random.Random(seed)
        arrivals: list[DemandEvent] = []
        for profile in sorted(profiles, key=lambda item: item.profile_id):
            probability = min(profile.rate_per_hour / self.ticks_per_hour, 1.0)
            for tick in range(profile.start_tick, profile.end_tick + 1):
                if rng.random() >= probability:
                    continue
                for burst_index in range(profile.burst_size):
                    request_id = f"{profile.profile_id}-{tick:06d}-{burst_index:02d}"
                    arrivals.append(
                        DemandEvent(
                            request_id,
                            profile.location,
                            tick,
                            profile.zone,
                            profile.merchant_id,
                            profile.order_profile,
                        )
                    )
        ordered = tuple(sorted(arrivals, key=lambda item: (item.tick, item.request_id)))
        payload = {
            "seed": seed,
            "ticks_per_hour": self.ticks_per_hour,
            "profiles": [
                {
                    "profile_id": profile.profile_id,
                    "rate_per_hour": profile.rate_per_hour,
                    "start_tick": profile.start_tick,
                    "end_tick": profile.end_tick,
                    "location": (profile.location.latitude, profile.location.longitude),
                    "zone": profile.zone,
                    "merchant_id": profile.merchant_id,
                    "order_profile": profile.order_profile,
                    "burst_size": profile.burst_size,
                }
                for profile in sorted(profiles, key=lambda item: item.profile_id)
            ],
            "arrivals": [
                {
                    "request_id": arrival.request_id,
                    "tick": arrival.tick,
                    "zone": arrival.zone,
                    "merchant_id": arrival.merchant_id,
                    "order_profile": arrival.order_profile,
                }
                for arrival in ordered
            ],
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return DemandArrivalRun(
            seed,
            tuple(sorted(profiles, key=lambda item: item.profile_id)),
            ordered,
            digest,
        )
