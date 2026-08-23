package com.routemind.business.application.operations;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record OperationsSnapshot(Instant generatedAt, List<OrderSummary> orders, List<PartySummary> parties,
		List<CourierLocationSummary> courierLocations) {

	public OperationsSnapshot {
		if (generatedAt == null) {
			throw new IllegalArgumentException("generatedAt is required");
		}
		orders = List.copyOf(orders);
		parties = List.copyOf(parties);
		courierLocations = List.copyOf(courierLocations);
	}

	public record OrderSummary(UUID id, String status, long version, Instant createdAt, Instant updatedAt) {
	}

	public record PartySummary(UUID id, String type, String displayName, String status) {
	}

	public record CourierLocationSummary(UUID courierId, double latitude, double longitude, long sequence,
			Instant observedAt, Instant ingestedAt, boolean online) {
		public CourierLocationSummary(UUID courierId, double latitude, double longitude, Instant observedAt) {
			this(courierId, latitude, longitude, 1, observedAt, observedAt, true);
		}
	}
}
