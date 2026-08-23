package com.routemind.business.application.courier;

import java.util.Map;
import java.util.Set;
import java.util.UUID;

public record CourierProjectionInspection(Status status, Set<UUID> courierIds, Map<String, String> evidence) {

	public enum Status {
		AVAILABLE,
		UNAVAILABLE
	}

	public CourierProjectionInspection {
		if (status == null) throw new IllegalArgumentException("projection inspection status is required");
		courierIds = Set.copyOf(courierIds);
		evidence = Map.copyOf(evidence);
		if (status == Status.UNAVAILABLE && !courierIds.isEmpty()) {
			throw new IllegalArgumentException("unavailable projection cannot claim members");
		}
	}

	public static CourierProjectionInspection unavailable(String reason) {
		return new CourierProjectionInspection(Status.UNAVAILABLE, Set.of(), Map.of("reason", reason));
	}
}
