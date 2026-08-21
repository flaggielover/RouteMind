package com.routemind.business.domain.order;

import java.time.Instant;
import java.util.List;
import java.util.Objects;

public record Order(OrderId id, OrderStatus status, long version, Instant createdAt,
		Instant updatedAt, List<OrderTransition> transitions) {

	public Order {
		Objects.requireNonNull(id, "id");
		Objects.requireNonNull(status, "status");
		if (version < 0) {
			throw new IllegalArgumentException("version must not be negative");
		}
		Objects.requireNonNull(createdAt, "createdAt");
		Objects.requireNonNull(updatedAt, "updatedAt");
		if (updatedAt.isBefore(createdAt)) {
			throw new IllegalArgumentException("updatedAt must not precede createdAt");
		}
		transitions = List.copyOf(Objects.requireNonNull(transitions, "transitions"));
	}

	public static Order create(OrderId id, Instant createdAt) {
		return new Order(id, OrderStatus.CREATED, 0, createdAt, createdAt, List.of());
	}

	public Order transitionTo(OrderStatus target, String actor, Instant occurredAt,
			long expectedVersion) {
		Objects.requireNonNull(target, "target");
		if (expectedVersion != version) {
			throw new IllegalStateException("stale order version: expected " + expectedVersion
					+ ", actual " + version);
		}
		if (!status.canTransitionTo(target)) {
			throw new IllegalStateException("invalid order transition: " + status + " -> " + target);
		}
		if (occurredAt == null || !occurredAt.isAfter(updatedAt)) {
			throw new IllegalArgumentException("occurredAt must advance updatedAt");
		}
		var next = new java.util.ArrayList<>(transitions);
		next.add(new OrderTransition(version + 1, status, target, actor, occurredAt));
		return new Order(id, target, version + 1, createdAt, occurredAt, next);
	}
}
