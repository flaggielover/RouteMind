package com.routemind.business.application.order;

import java.time.Instant;
import java.util.UUID;
import java.util.regex.Pattern;

public record OrderCommandIdempotency(String key, String requestHash, String operation, UUID orderId,
		String status, long version, Instant createdAt) {

	private static final Pattern HASH = Pattern.compile("[0-9a-f]{64}");

	public OrderCommandIdempotency {
		if (key == null || key.isBlank() || key.length() > 128 || key.chars().anyMatch(Character::isISOControl)) {
			throw new IllegalArgumentException("idempotency key must be 1-128 safe characters");
		}
		if (requestHash == null || !HASH.matcher(requestHash).matches()) {
			throw new IllegalArgumentException("request hash must be a lowercase SHA-256 digest");
		}
		if (operation == null || operation.isBlank() || orderId == null || status == null || status.isBlank()
				|| version < 0 || createdAt == null) {
			throw new IllegalArgumentException("idempotency record fields are required");
		}
	}
}
