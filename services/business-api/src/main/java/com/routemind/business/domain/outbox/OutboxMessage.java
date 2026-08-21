package com.routemind.business.domain.outbox;

import com.routemind.business.domain.event.EventEnvelope;
import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

public record OutboxMessage(UUID id, EventEnvelope event, OutboxStatus status, int attempts,
		Instant nextAttemptAt, Instant createdAt, Instant publishedAt, String lastError) {

	public OutboxMessage {
		Objects.requireNonNull(id, "id");
		Objects.requireNonNull(event, "event");
		Objects.requireNonNull(status, "status");
		if (attempts < 0) {
			throw new IllegalArgumentException("attempts must not be negative");
		}
		Objects.requireNonNull(nextAttemptAt, "nextAttemptAt");
		Objects.requireNonNull(createdAt, "createdAt");
	}

	public static OutboxMessage pending(EventEnvelope event) {
		Instant now = event.occurredAt();
		return new OutboxMessage(event.eventId(), event, OutboxStatus.PENDING, 0, now, now, null, null);
	}

	public OutboxMessage claim(Instant now) {
		if (status != OutboxStatus.PENDING && status != OutboxStatus.RETRYABLE) {
			throw new IllegalStateException("outbox message is not claimable: " + status);
		}
		return new OutboxMessage(id, event, OutboxStatus.IN_FLIGHT, attempts, now, createdAt, publishedAt, lastError);
	}

	public OutboxMessage published(Instant now) {
		if (status != OutboxStatus.IN_FLIGHT) {
			throw new IllegalStateException("outbox message is not in flight");
		}
		return new OutboxMessage(id, event, OutboxStatus.PUBLISHED, attempts, nextAttemptAt, createdAt, now, null);
	}

	public OutboxMessage retry(Instant now, String error) {
		if (status != OutboxStatus.IN_FLIGHT) {
			throw new IllegalStateException("outbox message is not in flight");
		}
		int nextAttempts = Math.min(attempts + 1, 8);
		long delaySeconds = Math.min(60, 1L << Math.min(nextAttempts, 6));
		return new OutboxMessage(id, event, OutboxStatus.RETRYABLE, nextAttempts,
				now.plusSeconds(delaySeconds), createdAt, publishedAt,
				error == null || error.isBlank() ? "publish failed" : error.trim());
	}
}
