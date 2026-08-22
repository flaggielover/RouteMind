package com.routemind.business.domain.courier;

import java.time.Instant;
import java.util.UUID;

public record CourierShift(UUID courierId, CourierShiftStatus status, long version, Instant updatedAt) {

	public CourierShift {
		if (courierId == null) throw new IllegalArgumentException("courierId is required");
		if (status == null) throw new IllegalArgumentException("status is required");
		if (version < 0) throw new IllegalArgumentException("version must be non-negative");
		if (updatedAt == null) throw new IllegalArgumentException("updatedAt is required");
	}

	public static CourierShift offline(UUID courierId, Instant now) {
		return new CourierShift(courierId, CourierShiftStatus.OFFLINE, 0, now);
	}

	public CourierShift transitionTo(CourierShiftStatus target, long expectedVersion, Instant now) {
		if (version != expectedVersion) throw new IllegalStateException("stale_version");
		if (target == status) throw new IllegalStateException("shift_already_" + target.name().toLowerCase());
		if (status == CourierShiftStatus.OFFLINE && target != CourierShiftStatus.ONLINE) {
			throw new IllegalStateException("invalid_shift_transition");
		}
		if (status == CourierShiftStatus.ONLINE && target != CourierShiftStatus.OFFLINE) {
			throw new IllegalStateException("invalid_shift_transition");
		}
		return new CourierShift(courierId, target, version + 1, now);
	}
}
