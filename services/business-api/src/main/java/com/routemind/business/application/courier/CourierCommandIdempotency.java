package com.routemind.business.application.courier;

import java.time.Instant;
import java.util.UUID;

public record CourierCommandIdempotency(String key, String requestHash, String operation, UUID courierId,
		String status, long version, Instant createdAt) {
}
