package com.routemind.business.application.order;

import com.routemind.business.application.outbox.OutboxRepository;
import com.routemind.business.domain.event.EventEnvelope;
import com.routemind.business.domain.order.Order;
import com.routemind.business.domain.order.OrderId;
import com.routemind.business.domain.order.OrderStatus;
import com.routemind.business.domain.outbox.OutboxMessage;
import java.time.Clock;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class OrderCommandService {

	private final OrderRepository orders;
	private final OutboxRepository outbox;
	private final Clock clock;

	public OrderCommandService(OrderRepository orders, OutboxRepository outbox, Clock clock) {
		this.orders = orders;
		this.outbox = outbox;
		this.clock = clock;
	}

	@Transactional
	public Order transition(OrderId id, OrderStatus target, String actor, long expectedVersion,
			UUID correlationId, UUID causationId, String traceId) {
		Order current = orders.findById(id).orElseThrow();
		Order next = current.transitionTo(target, actor, clock.instant(), expectedVersion);
		Order saved = orders.save(next);
		EventEnvelope event = new EventEnvelope("1.0", UUID.randomUUID(), "order.status.changed",
				clock.instant(), "business-api", id.value(), saved.version(), correlationId, causationId,
				traceId, Map.of("orderId", id.value().toString(), "status", target.name(), "actor", actor));
		outbox.save(OutboxMessage.pending(event));
		return saved;
	}
}
