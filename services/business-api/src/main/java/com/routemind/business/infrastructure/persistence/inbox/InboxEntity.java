package com.routemind.business.infrastructure.persistence.inbox;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.routemind.business.domain.event.EventEnvelope;
import com.routemind.business.domain.inbox.InboxMessage;
import com.routemind.business.domain.inbox.InboxStatus;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "inbox_messages", schema = "routemind")
class InboxEntity {

	@Id
	@Column(name = "event_id")
	private UUID eventId;
	@Column(name = "event_type", nullable = false, length = 120) private String eventType;
	@Column(name = "occurred_at", nullable = false) private Instant occurredAt;
	@Column(nullable = false, length = 120) private String producer;
	@Column(name = "aggregate_id", nullable = false) private UUID aggregateId;
	@Column(name = "aggregate_version", nullable = false) private long aggregateVersion;
	@Column(name = "correlation_id", nullable = false) private UUID correlationId;
	@Column(name = "causation_id") private UUID causationId;
	@Column(name = "trace_id", nullable = false, length = 32) private String traceId;
	@Column(name = "payload_json", nullable = false, columnDefinition = "TEXT") private String payloadJson;
	@Enumerated(EnumType.STRING) @Column(nullable = false, length = 16) private InboxStatus status;
	@Column(nullable = false) private int attempts;
	@Column(name = "next_attempt_at", nullable = false) private Instant nextAttemptAt;
	@Column(name = "received_at", nullable = false) private Instant receivedAt;
	@Column(name = "processed_at") private Instant processedAt;
	@Column(name = "last_error", length = 500) private String lastError;

	protected InboxEntity() {
	}

	static InboxEntity from(InboxMessage message, ObjectMapper mapper) {
		InboxEntity entity = new InboxEntity();
		entity.apply(message, mapper);
		return entity;
	}

	void apply(InboxMessage message, ObjectMapper mapper) {
		eventId = message.eventId();
		eventType = message.event().eventType();
		occurredAt = message.event().occurredAt();
		producer = message.event().producer();
		aggregateId = message.event().aggregateId();
		aggregateVersion = message.event().aggregateVersion();
		correlationId = message.event().correlationId();
		causationId = message.event().causationId();
		traceId = message.event().traceId();
		try {
			payloadJson = mapper.writeValueAsString(message.event().payload());
		} catch (JsonProcessingException exception) {
			throw new IllegalArgumentException("event payload cannot be serialized", exception);
		}
		status = message.status();
		attempts = message.attempts();
		nextAttemptAt = message.nextAttemptAt();
		receivedAt = message.receivedAt();
		processedAt = message.processedAt();
		lastError = message.lastError();
	}

	InboxMessage toDomain(ObjectMapper mapper) {
		try {
			var payload = mapper.readValue(payloadJson, new TypeReference<java.util.Map<String, Object>>() { });
			EventEnvelope event = new EventEnvelope("1.0", eventId, eventType, occurredAt, producer,
					aggregateId, aggregateVersion, correlationId, causationId, traceId, payload);
			return new InboxMessage(eventId, event, status, attempts, nextAttemptAt, receivedAt,
					processedAt, lastError);
		} catch (JsonProcessingException exception) {
			throw new IllegalStateException("stored event payload cannot be read", exception);
		}
	}
}
