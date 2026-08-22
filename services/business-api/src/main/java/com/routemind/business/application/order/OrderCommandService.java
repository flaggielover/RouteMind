package com.routemind.business.application.order;

import com.routemind.business.application.outbox.OutboxRepository;
import com.routemind.business.domain.event.EventEnvelope;
import com.routemind.business.domain.order.Order;
import com.routemind.business.domain.order.OrderId;
import com.routemind.business.domain.order.OrderStatus;
import com.routemind.business.domain.outbox.OutboxMessage;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Map;
import java.util.UUID;
import java.util.HexFormat;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class OrderCommandService {

	private final OrderRepository orders;
	private final OutboxRepository outbox;
	private final OrderCommandIdempotencyRepository idempotency;
	private final Clock clock;

	public OrderCommandService(OrderRepository orders, OutboxRepository outbox,
			OrderCommandIdempotencyRepository idempotency, Clock clock) {
		this.orders = orders;
		this.outbox = outbox;
		this.idempotency = idempotency;
		this.clock = clock;
	}

	@Transactional
	public Order transition(OrderId id, OrderStatus target, String actor, long expectedVersion,
			UUID correlationId, UUID causationId, String traceId) {
		transitionCommand(id, target, actor, expectedVersion, correlationId, causationId, traceId,
				UUID.randomUUID().toString());
		return orders.findById(id).orElseThrow();
	}

	@Transactional
	public OrderCommandResult create(String actor, UUID correlationId, UUID causationId, String traceId,
			String idempotencyKey) {
		idempotencyKey = requireKey(idempotencyKey);
		OrderCommandAuthorization.requireCreate(actor);
		String requestHash = fingerprint("create", actor);
		OrderCommandResult replay = replayIfPresent(idempotencyKey, requestHash, "create");
		if (replay != null) {
			return replay;
		}
		Order created = Order.create(OrderId.newId(), clock.instant());
		Order saved = orders.save(created);
		publish(saved, correlationId, causationId, traceId, "order.created", actor, 1);
		idempotency.save(new OrderCommandIdempotency(idempotencyKey, requestHash, "create", saved.id().value(),
				saved.status().name(), saved.version(), clock.instant()));
		return new OrderCommandResult(saved.id().value(), saved.status().name(), saved.version(), false);
	}

	@Transactional
	public OrderCommandResult transitionCommand(OrderId id, OrderStatus target, String actor, long expectedVersion,
			UUID correlationId, UUID causationId, String traceId, String idempotencyKey) {
		idempotencyKey = requireKey(idempotencyKey);
		Order current = orders.findById(id).orElseThrow();
		String requestHash = fingerprint("transition", id.value().toString(), target.name(), actor,
				Long.toString(expectedVersion));
		OrderCommandResult replay = replayIfPresent(idempotencyKey, requestHash, "transition");
		if (replay != null) {
			return replay;
		}
		if (current.version() != expectedVersion) {
			throw new OrderCommandConflictException("stale_version");
		}
		OrderCommandAuthorization.requireTransition(actor, current.status(), target);
		Order next = current.transitionTo(target, actor, clock.instant(), expectedVersion);
		Order saved = orders.save(next);
		publish(saved, correlationId, causationId, traceId, "order.status.changed", actor, saved.version());
		idempotency.save(new OrderCommandIdempotency(idempotencyKey, requestHash, "transition", saved.id().value(),
				saved.status().name(), saved.version(), clock.instant()));
		return new OrderCommandResult(saved.id().value(), saved.status().name(), saved.version(), false);
	}

	private OrderCommandResult replayIfPresent(String key, String requestHash, String operation) {
		OrderCommandIdempotency existing = idempotency.findByKey(key).orElse(null);
		if (existing == null) {
			return null;
		}
		if (!existing.requestHash().equals(requestHash) || !existing.operation().equals(operation)) {
			throw new OrderCommandConflictException("idempotency_key_reused");
		}
		return new OrderCommandResult(existing.orderId(), existing.status(), existing.version(), true);
	}

	private static String requireKey(String key) {
		if (key == null || key.isBlank() || key.length() > 128 || key.chars().anyMatch(Character::isISOControl)) {
			throw new IllegalArgumentException("idempotency key must be 1-128 safe characters");
		}
		return key.trim();
	}

	private void publish(Order saved, UUID correlationId, UUID causationId, String traceId, String eventType,
			String actor, long aggregateVersion) {
		EventEnvelope event = new EventEnvelope("1.0", UUID.randomUUID(), eventType, clock.instant(), "business-api",
				saved.id().value(), aggregateVersion, correlationId, causationId, traceId,
				Map.of("orderId", saved.id().value().toString(), "status", saved.status().name(), "actor", actor));
		outbox.save(OutboxMessage.pending(event));
	}

	private static String fingerprint(String... fields) {
		try {
			MessageDigest digest = MessageDigest.getInstance("SHA-256");
			for (String field : fields) {
				byte[] bytes = field.getBytes(StandardCharsets.UTF_8);
				digest.update(Integer.toString(bytes.length).getBytes(StandardCharsets.US_ASCII));
				digest.update((byte) ':');
				digest.update(bytes);
			}
			return HexFormat.of().formatHex(digest.digest());
		}
		catch (NoSuchAlgorithmException exception) {
			throw new IllegalStateException("SHA-256 is unavailable", exception);
		}
	}

}
