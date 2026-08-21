package com.routemind.business.infrastructure.persistence.outbox;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.routemind.business.domain.event.EventEnvelope;
import com.routemind.business.domain.outbox.OutboxMessage;
import com.routemind.business.domain.outbox.OutboxStatus;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "outbox_messages", schema = "routemind")
class OutboxEntity {

	@Id
	@Column(name = "event_id")
	private UUID eventId;

	@Column(name = "event_type", nullable = false, length = 120)
	private String eventType;

	@Column(name = "occurred_at", nullable = false)
	private Instant occurredAt;

	@Column(nullable = false, length = 120)
	private String producer;

	@Column(name = "aggregate_id", nullable = false)
	private UUID aggregateId;

	@Column(name = "aggregate_version", nullable = false)
	private long aggregateVersion;

	@Column(name = "correlation_id", nullable = false)
	private UUID correlationId;

	@Column(name = "causation_id")
	private UUID causationId;

	@Column(name = "trace_id", nullable = false, length = 32)
	private String traceId;

	@Column(name = "payload_json", nullable = false, columnDefinition = "TEXT")
	private String payloadJson;

	@Enumerated(EnumType.STRING)
	@Column(nullable = false, length = 16)
	private OutboxStatus status;

	@Column(nullable = false)
	private int attempts;

	@Column(name = "next_attempt_at", nullable = false)
	private Instant nextAttemptAt;

	@Column(name = "created_at", nullable = false)
	private Instant createdAt;

	@Column(name = "published_at")
	private Instant publishedAt;

	@Column(name = "last_error", length = 500)
	private String lastError;

	protected OutboxEntity() {
	}

	private OutboxEntity(OutboxMessage message, ObjectMapper mapper) {
		apply(message, mapper);
	}

	static OutboxEntity from(OutboxMessage message, ObjectMapper mapper) {
		return new OutboxEntity(message, mapper);
	}

	void apply(OutboxMessage message, ObjectMapper mapper) {
		eventId = message.id();
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
		createdAt = message.createdAt();
		publishedAt = message.publishedAt();
		lastError = message.lastError();
	}

	OutboxMessage toDomain(ObjectMapper mapper) {
		try {
			var payload = mapper.readValue(payloadJson, new TypeReference<java.util.Map<String, Object>>() {
			});
			EventEnvelope event = new EventEnvelope("1.0", eventId, eventType, occurredAt, producer,
					aggregateId, aggregateVersion, correlationId, causationId, traceId, payload);
			return new OutboxMessage(eventId, event, status, attempts, nextAttemptAt, createdAt,
					publishedAt, lastError);
		} catch (JsonProcessingException exception) {
			throw new IllegalStateException("stored event payload cannot be read", exception);
		}
	}
}
