package com.routemind.business.domain.order;

import java.time.Instant;
import java.util.Objects;

public record OrderTransition(long sequenceNumber, OrderStatus from, OrderStatus to,
		String actor, Instant occurredAt) {

	public OrderTransition {
		if (sequenceNumber < 1) {
			throw new IllegalArgumentException("sequenceNumber must be positive");
		}
		Objects.requireNonNull(from, "from");
		Objects.requireNonNull(to, "to");
		if (actor == null || actor.isBlank()) {
			throw new IllegalArgumentException("actor must not be blank");
		}
		actor = actor.trim();
		Objects.requireNonNull(occurredAt, "occurredAt");
	}
}
