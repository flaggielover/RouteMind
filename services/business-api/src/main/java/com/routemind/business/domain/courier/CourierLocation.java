package com.routemind.business.domain.courier;

import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

public record CourierLocation(UUID courierId, GeoPoint point, Instant observedAt) {

	public CourierLocation {
		Objects.requireNonNull(courierId, "courierId");
		Objects.requireNonNull(point, "point");
		Objects.requireNonNull(observedAt, "observedAt");
	}
}
