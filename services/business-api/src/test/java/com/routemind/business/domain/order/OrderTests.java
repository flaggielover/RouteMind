package com.routemind.business.domain.order;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;
import static org.assertj.core.api.Assertions.assertThatIllegalStateException;

import java.time.Instant;
import org.junit.jupiter.api.Test;

class OrderTests {

	private final Instant created = Instant.parse("2026-01-01T00:00:00Z");

	@Test
	void followsTheHappyPathAndRecordsEveryTransition() {
		Order order = Order.create(OrderId.newId(), created)
				.transitionTo(OrderStatus.CONFIRMED, "customer", created.plusSeconds(1), 0)
				.transitionTo(OrderStatus.ASSIGNED, "dispatch", created.plusSeconds(2), 1)
				.transitionTo(OrderStatus.PICKED_UP, "courier", created.plusSeconds(3), 2)
				.transitionTo(OrderStatus.DELIVERED, "courier", created.plusSeconds(4), 3);

		assertThat(order.status()).isEqualTo(OrderStatus.DELIVERED);
		assertThat(order.version()).isEqualTo(4);
		assertThat(order.transitions()).extracting(OrderTransition::sequenceNumber)
				.containsExactly(1L, 2L, 3L, 4L);
	}

	@Test
	void rejectsForbiddenRepeatedAndStaleTransitions() {
		Order order = Order.create(OrderId.newId(), created)
				.transitionTo(OrderStatus.CONFIRMED, "customer", created.plusSeconds(1), 0);

		assertThatIllegalStateException().isThrownBy(() ->
				order.transitionTo(OrderStatus.CREATED, "customer", created.plusSeconds(2), 1));
		assertThatIllegalStateException().isThrownBy(() ->
				order.transitionTo(OrderStatus.ASSIGNED, "dispatch", created.plusSeconds(2), 0));
	}

	@Test
	void recordsMerchantPreparationAndReadyStatesBeforeDispatch() {
		Order order = Order.create(OrderId.newId(), created)
				.transitionTo(OrderStatus.CONFIRMED, "merchant", created.plusSeconds(1), 0)
				.transitionTo(OrderStatus.PREPARING, "merchant", created.plusSeconds(2), 1)
				.transitionTo(OrderStatus.READY_FOR_PICKUP, "merchant", created.plusSeconds(3), 2)
				.transitionTo(OrderStatus.ASSIGNED, "dispatch", created.plusSeconds(4), 3);

		assertThat(order.status()).isEqualTo(OrderStatus.ASSIGNED);
		assertThat(order.transitions()).extracting(OrderTransition::to)
				.containsExactly(OrderStatus.CONFIRMED, OrderStatus.PREPARING,
						OrderStatus.READY_FOR_PICKUP, OrderStatus.ASSIGNED);
	}

	@Test
	void cancellationIsOnlyAllowedBeforePickupAndTimeMustAdvance() {
		Order cancelled = Order.create(OrderId.newId(), created)
				.transitionTo(OrderStatus.CANCELLED, "customer", created.plusSeconds(1), 0);

		assertThatIllegalStateException().isThrownBy(() ->
				cancelled.transitionTo(OrderStatus.CONFIRMED, "customer", created.plusSeconds(2), 1));
		assertThatIllegalArgumentException().isThrownBy(() ->
				Order.create(OrderId.newId(), created).transitionTo(
						OrderStatus.CONFIRMED, "customer", created, 0));
	}
}
