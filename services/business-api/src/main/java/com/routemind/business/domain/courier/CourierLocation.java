package com.routemind.business.domain.courier;

import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

public record CourierLocation(UUID courierId, GeoPoint point, long sequence, Instant observedAt,
		Instant ingestedAt, boolean online) {

	public CourierLocation {
		Objects.requireNonNull(courierId, "courierId");
		Objects.requireNonNull(point, "point");
		if (sequence < 1) throw new IllegalArgumentException("sequence must be positive");
		Objects.requireNonNull(observedAt, "observedAt");
		Objects.requireNonNull(ingestedAt, "ingestedAt");
	}

	public CourierLocation(UUID courierId, GeoPoint point, Instant observedAt) {
		this(courierId, point, 1, observedAt, observedAt, true);
	}
}
