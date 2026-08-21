package com.routemind.business.domain.event;

import java.time.Instant;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import java.util.regex.Pattern;

public record EventEnvelope(String specVersion, UUID eventId, String eventType, Instant occurredAt,
		String producer, UUID aggregateId, long aggregateVersion, UUID correlationId,
		UUID causationId, String traceId, Map<String, Object> payload) {

	private static final Pattern EVENT_TYPE = Pattern.compile("^[a-z][a-z0-9]*(\\.[a-z][a-z0-9]*)+$");
	private static final Pattern TRACE_ID = Pattern.compile("^[0-9a-f]{32}$");

	public EventEnvelope {
		if (!"1.0".equals(specVersion)) {
			throw new IllegalArgumentException("specVersion must be 1.0");
		}
		Objects.requireNonNull(eventId, "eventId");
		if (eventType == null || !EVENT_TYPE.matcher(eventType).matches()) {
			throw new IllegalArgumentException("eventType must be a dotted lowercase name");
		}
		Objects.requireNonNull(occurredAt, "occurredAt");
		if (producer == null || producer.isBlank()) {
			throw new IllegalArgumentException("producer must not be blank");
		}
		Objects.requireNonNull(aggregateId, "aggregateId");
		if (aggregateVersion < 1) {
			throw new IllegalArgumentException("aggregateVersion must be positive");
		}
		Objects.requireNonNull(correlationId, "correlationId");
		if (traceId == null || !TRACE_ID.matcher(traceId).matches()) {
			throw new IllegalArgumentException("traceId must be 32 lowercase hex characters");
		}
		payload = Map.copyOf(Objects.requireNonNull(payload, "payload"));
	}
}
