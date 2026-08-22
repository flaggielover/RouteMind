from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field, replace
from math import isfinite
from typing import Literal

from routemind_compute.domain.dispatch import DispatchProblem

PreparationStatus = Literal["scheduled", "queued", "preparing", "ready"]


@dataclass(frozen=True, slots=True)
class MerchantPreparationProfile:
    merchant_id: str
    base_prep_seconds: float
    variability_seconds: float = 0.0
    capacity: int = 1
    order_profile_multipliers: tuple[tuple[str, float], ...] = (("standard", 1.0),)
    late_risk_horizon_seconds: float = 300.0

    def __post_init__(self) -> None:
        if not self.merchant_id.strip():
            raise ValueError("merchant id must not be blank")
        if not isfinite(self.base_prep_seconds) or self.base_prep_seconds < 0:
            raise ValueError("base preparation seconds must be finite and non-negative")
        if not isfinite(self.variability_seconds) or self.variability_seconds < 0:
            raise ValueError("preparation variability must be finite and non-negative")
        if (
            not isinstance(self.capacity, int)
            or isinstance(self.capacity, bool)
            or self.capacity <= 0
        ):
            raise ValueError("preparation capacity must be a positive integer")
        if not isfinite(self.late_risk_horizon_seconds) or self.late_risk_horizon_seconds <= 0:
            raise ValueError("late risk horizon must be finite and positive")
        profile_ids = [profile_id for profile_id, _ in self.order_profile_multipliers]
        if len(profile_ids) != len(set(profile_ids)):
            raise ValueError("order profile identifiers must be unique")
        for profile_id, multiplier in self.order_profile_multipliers:
            if not profile_id.strip():
                raise ValueError("order profile identifier must not be blank")
            if not isfinite(multiplier) or multiplier <= 0:
                raise ValueError("order profile multiplier must be finite and positive")

    def multiplier_for(self, order_profile: str) -> float:
        for profile_id, multiplier in self.order_profile_multipliers:
            if profile_id == order_profile:
                return multiplier
        raise ValueError(f"unknown order profile for merchant: {order_profile}")


@dataclass(frozen=True, slots=True)
class PreparationOrder:
    order_id: str
    merchant_id: str
    enqueued_at_seconds: float
    order_profile: str = "standard"

    def __post_init__(self) -> None:
        if not self.order_id.strip():
            raise ValueError("preparation order id must not be blank")
        if not self.merchant_id.strip():
            raise ValueError("preparation merchant id must not be blank")
        if not isfinite(self.enqueued_at_seconds) or self.enqueued_at_seconds < 0:
            raise ValueError("enqueued time must be finite and non-negative")
        if not self.order_profile.strip():
            raise ValueError("preparation order profile must not be blank")


@dataclass(frozen=True, slots=True)
class _ScheduledPreparation:
    order: PreparationOrder
    expected_prep_seconds: float
    actual_prep_seconds: float
    expected_start_at_seconds: float
    actual_start_at_seconds: float
    expected_ready_at_seconds: float
    actual_ready_at_seconds: float


@dataclass(frozen=True, slots=True)
class MerchantPreparationState:
    order_id: str
    merchant_id: str
    order_profile: str
    observed_at_seconds: float
    queue_load: int
    expected_prep_seconds: float
    actual_prep_seconds: float
    expected_start_at_seconds: float
    actual_start_at_seconds: float
    expected_ready_at_seconds: float
    actual_ready_at_seconds: float
    late_risk: float
    status: PreparationStatus

    def __post_init__(self) -> None:
        if not self.order_id.strip() or not self.merchant_id.strip():
            raise ValueError("preparation state identifiers must not be blank")
        if not self.order_profile.strip():
            raise ValueError("preparation state order profile must not be blank")
        if not isfinite(self.observed_at_seconds) or self.observed_at_seconds < 0:
            raise ValueError("observed time must be finite and non-negative")
        if self.queue_load < 0:
            raise ValueError("queue load must be non-negative")
        times = (
            self.expected_prep_seconds,
            self.actual_prep_seconds,
            self.expected_start_at_seconds,
            self.actual_start_at_seconds,
            self.expected_ready_at_seconds,
            self.actual_ready_at_seconds,
        )
        if any(not isfinite(value) or value < 0 for value in times):
            raise ValueError("preparation times must be finite and non-negative")
        if not isfinite(self.late_risk) or not 0 <= self.late_risk <= 1:
            raise ValueError("late risk must be between 0 and 1")
        if self.status not in {"scheduled", "queued", "preparing", "ready"}:
            raise ValueError("preparation status is not supported")

    @property
    def dispatch_ready_at_seconds(self) -> float:
        """Use the simulated actual-ready boundary when dispatching this state."""
        return max(self.observed_at_seconds, self.actual_ready_at_seconds)

    def apply_to(self, problem: DispatchProblem) -> DispatchProblem:
        if problem.request_id != self.order_id:
            raise ValueError("preparation state order does not match dispatch request")
        return replace(problem, pickup_ready_at_seconds=self.dispatch_ready_at_seconds)


@dataclass(frozen=True, slots=True)
class MerchantPreparationRun:
    seed: int
    profiles: tuple[MerchantPreparationProfile, ...]
    orders: tuple[PreparationOrder, ...]
    replay_digest: str
    _scheduled: tuple[_ScheduledPreparation, ...] = field(repr=False)

    def _find(self, order_id: str) -> _ScheduledPreparation:
        for scheduled in self._scheduled:
            if scheduled.order.order_id == order_id:
                return scheduled
        raise KeyError(f"unknown preparation order: {order_id}")

    def state_at(self, order_id: str, simulated_time_seconds: float) -> MerchantPreparationState:
        if not isfinite(simulated_time_seconds) or simulated_time_seconds < 0:
            raise ValueError("observed time must be finite and non-negative")
        scheduled = self._find(order_id)
        profile = next(
            profile
            for profile in self.profiles
            if profile.merchant_id == scheduled.order.merchant_id
        )
        observed = simulated_time_seconds
        if observed < scheduled.order.enqueued_at_seconds:
            status: PreparationStatus = "scheduled"
        elif observed < scheduled.actual_start_at_seconds:
            status = "queued"
        elif observed < scheduled.actual_ready_at_seconds:
            status = "preparing"
        else:
            status = "ready"
        queue_load = sum(
            item.order.merchant_id == scheduled.order.merchant_id
            and item.order.enqueued_at_seconds <= observed < item.actual_ready_at_seconds
            for item in self._scheduled
        )
        late_seconds = max(
            0.0,
            min(observed, scheduled.actual_ready_at_seconds) - scheduled.expected_ready_at_seconds,
        )
        late_risk = min(1.0, late_seconds / profile.late_risk_horizon_seconds)
        return MerchantPreparationState(
            scheduled.order.order_id,
            scheduled.order.merchant_id,
            scheduled.order.order_profile,
            observed,
            queue_load,
            scheduled.expected_prep_seconds,
            scheduled.actual_prep_seconds,
            scheduled.expected_start_at_seconds,
            scheduled.actual_start_at_seconds,
            scheduled.expected_ready_at_seconds,
            scheduled.actual_ready_at_seconds,
            late_risk,
            status,
        )

    def states_at(self, simulated_time_seconds: float) -> tuple[MerchantPreparationState, ...]:
        return tuple(self.state_at(order.order_id, simulated_time_seconds) for order in self.orders)


class MerchantPreparationModel:
    """Produce deterministic merchant preparation schedules for twin scenarios."""

    def __init__(
        self,
        profiles: tuple[MerchantPreparationProfile, ...],
        seed: int,
    ) -> None:
        if not profiles:
            raise ValueError("at least one merchant preparation profile is required")
        merchant_ids = [profile.merchant_id for profile in profiles]
        if len(merchant_ids) != len(set(merchant_ids)):
            raise ValueError("merchant preparation identifiers must be unique")
        self.profiles = tuple(sorted(profiles, key=lambda profile: profile.merchant_id))
        self.seed = seed

    def run(self, orders: tuple[PreparationOrder, ...]) -> MerchantPreparationRun:
        order_ids = [order.order_id for order in orders]
        if len(order_ids) != len(set(order_ids)):
            raise ValueError("preparation order identifiers must be unique")
        profiles = {profile.merchant_id: profile for profile in self.profiles}
        ordered = tuple(
            sorted(orders, key=lambda order: (order.enqueued_at_seconds, order.order_id))
        )
        expected_slots = {
            profile.merchant_id: [0.0] * profile.capacity for profile in self.profiles
        }
        actual_slots = {profile.merchant_id: [0.0] * profile.capacity for profile in self.profiles}
        rng = random.Random(self.seed)
        scheduled: list[_ScheduledPreparation] = []
        for order in ordered:
            profile = profiles.get(order.merchant_id)
            if profile is None:
                raise ValueError(f"unknown merchant preparation profile: {order.merchant_id}")
            expected_prep = profile.base_prep_seconds * profile.multiplier_for(order.order_profile)
            jitter = (
                rng.uniform(-profile.variability_seconds, profile.variability_seconds)
                if profile.variability_seconds
                else 0.0
            )
            actual_prep = max(0.0, expected_prep + jitter)
            expected_slot = min(
                range(profile.capacity),
                key=lambda index: (expected_slots[order.merchant_id][index], index),
            )
            actual_slot = min(
                range(profile.capacity),
                key=lambda index: (actual_slots[order.merchant_id][index], index),
            )
            expected_start = max(
                order.enqueued_at_seconds, expected_slots[order.merchant_id][expected_slot]
            )
            actual_start = max(
                order.enqueued_at_seconds, actual_slots[order.merchant_id][actual_slot]
            )
            expected_ready = expected_start + expected_prep
            actual_ready = actual_start + actual_prep
            expected_slots[order.merchant_id][expected_slot] = expected_ready
            actual_slots[order.merchant_id][actual_slot] = actual_ready
            scheduled.append(
                _ScheduledPreparation(
                    order,
                    expected_prep,
                    actual_prep,
                    expected_start,
                    actual_start,
                    expected_ready,
                    actual_ready,
                )
            )
        payload = {
            "seed": self.seed,
            "profiles": [
                {
                    "merchant_id": profile.merchant_id,
                    "base_prep_seconds": profile.base_prep_seconds,
                    "variability_seconds": profile.variability_seconds,
                    "capacity": profile.capacity,
                    "order_profile_multipliers": profile.order_profile_multipliers,
                    "late_risk_horizon_seconds": profile.late_risk_horizon_seconds,
                }
                for profile in self.profiles
            ],
            "orders": [
                {
                    "order_id": item.order.order_id,
                    "merchant_id": item.order.merchant_id,
                    "order_profile": item.order.order_profile,
                    "enqueued_at_seconds": item.order.enqueued_at_seconds,
                    "expected_prep_seconds": item.expected_prep_seconds,
                    "actual_prep_seconds": item.actual_prep_seconds,
                    "expected_start_at_seconds": item.expected_start_at_seconds,
                    "actual_start_at_seconds": item.actual_start_at_seconds,
                    "expected_ready_at_seconds": item.expected_ready_at_seconds,
                    "actual_ready_at_seconds": item.actual_ready_at_seconds,
                }
                for item in scheduled
            ],
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return MerchantPreparationRun(
            self.seed,
            self.profiles,
            ordered,
            digest,
            tuple(scheduled),
        )
