package com.routemind.business.domain.inbox;

import com.routemind.business.domain.event.EventEnvelope;
import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

public record InboxMessage(UUID eventId, EventEnvelope event, InboxStatus status, int attempts,
		Instant nextAttemptAt, Instant receivedAt, Instant processedAt, String lastError) {

	public InboxMessage {
		Objects.requireNonNull(eventId, "eventId");
		Objects.requireNonNull(event, "event");
		if (!eventId.equals(event.eventId())) {
			throw new IllegalArgumentException("eventId must match event envelope");
		}
		Objects.requireNonNull(status, "status");
		if (attempts < 0) {
			throw new IllegalArgumentException("attempts must not be negative");
		}
		Objects.requireNonNull(nextAttemptAt, "nextAttemptAt");
		Objects.requireNonNull(receivedAt, "receivedAt");
	}

	public static InboxMessage received(EventEnvelope event, Instant now) {
		return new InboxMessage(event.eventId(), event, InboxStatus.RECEIVED, 0, now, now, null, null);
	}

	public InboxMessage claim(Instant now) {
		if (status != InboxStatus.RECEIVED && status != InboxStatus.RETRYABLE
				&& status != InboxStatus.PROCESSING) {
			throw new IllegalStateException("inbox message is not claimable: " + status);
		}
		return new InboxMessage(eventId, event, InboxStatus.PROCESSING, attempts,
				now.plusSeconds(60), receivedAt, processedAt, lastError);
	}

	public InboxMessage processed(Instant now) {
		if (status != InboxStatus.PROCESSING) {
			throw new IllegalStateException("inbox message is not processing");
		}
		return new InboxMessage(eventId, event, InboxStatus.PROCESSED, attempts, nextAttemptAt,
				receivedAt, now, null);
	}

	public InboxMessage failed(Instant now, String error, int maxAttempts) {
		if (status != InboxStatus.PROCESSING) {
			throw new IllegalStateException("inbox message is not processing");
		}
		if (maxAttempts < 1) {
			throw new IllegalArgumentException("maxAttempts must be positive");
		}
		int nextAttempts = attempts + 1;
		InboxStatus nextStatus = nextAttempts >= maxAttempts ? InboxStatus.DEAD_LETTER : InboxStatus.RETRYABLE;
		long delay = Math.min(60, 1L << Math.min(nextAttempts, 6));
		return new InboxMessage(eventId, event, nextStatus, nextAttempts, now.plusSeconds(delay),
				receivedAt, processedAt, error == null || error.isBlank() ? "handler failed" : error.trim());
	}
}
