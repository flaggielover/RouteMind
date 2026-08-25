package com.routemind.business.application.order;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.routemind.business.application.outbox.OutboxRepository;
import com.routemind.business.domain.order.Order;
import com.routemind.business.domain.order.OrderId;
import com.routemind.business.domain.order.OrderStatus;
import com.routemind.business.domain.outbox.OutboxMessage;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

class OrderCommandClockTests {

	@Test
	void advancesTransitionTimeWhenTheClockHasNotAdvancedSinceCreation() {
		Instant now = Instant.parse("2026-08-24T12:00:00Z");
		Order initial = Order.create(OrderId.newId(), now);
		OrderRepository orders = mock(OrderRepository.class);
		OutboxRepository outbox = mock(OutboxRepository.class);
		OrderCommandIdempotencyRepository idempotency = mock(OrderCommandIdempotencyRepository.class);
		FulfillmentAssignmentCoordinator assignments = mock(FulfillmentAssignmentCoordinator.class);
		when(orders.findById(initial.id())).thenReturn(Optional.of(initial));
		when(orders.save(any(Order.class))).thenAnswer(invocation -> invocation.getArgument(0));
		when(idempotency.findByKey("fixed-clock-confirm")).thenReturn(Optional.empty());
		OrderCommandService commands = new OrderCommandService(orders, outbox, idempotency, assignments,
				Clock.fixed(now, ZoneOffset.UTC),
				new com.routemind.business.application.security.TenantContext());

		OrderCommandResult result = commands.transitionCommand(initial.id(), OrderStatus.CONFIRMED, "customer", 0,
				UUID.randomUUID(), null, "0123456789abcdef0123456789abcdef", "fixed-clock-confirm");

		ArgumentCaptor<Order> saved = ArgumentCaptor.forClass(Order.class);
		ArgumentCaptor<OutboxMessage> published = ArgumentCaptor.forClass(OutboxMessage.class);
		verify(orders).save(saved.capture());
		verify(outbox).save(published.capture());
		assertThat(result.status()).isEqualTo("CONFIRMED");
		assertThat(saved.getValue().updatedAt()).isEqualTo(now.plusNanos(1));
		assertThat(published.getValue().event().occurredAt()).isEqualTo(saved.getValue().updatedAt());
	}
}
