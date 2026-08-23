package com.routemind.business.application.order;

import static org.assertj.core.api.Assertions.assertThat;

import com.routemind.business.application.dispatch.DispatchAssignmentCommandService;
import com.routemind.business.domain.dispatch.DispatchAssignmentCommand;
import com.routemind.business.domain.order.Order;
import com.routemind.business.domain.order.OrderId;
import com.routemind.business.domain.order.OrderStatus;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

@SpringBootTest
@ActiveProfiles("test")
@Transactional
class FulfillmentSagaIntegrationTests {

	private static final String ZERO_DIGEST = "0".repeat(64);
	private static final String ONE_DIGEST = "1".repeat(64);
	private static final String TRACE_ID = "0123456789abcdef0123456789abcdef";

	@Autowired private OrderRepository orders;
	@Autowired private OrderCommandService commands;
	@Autowired private DispatchAssignmentCommandService assignments;
	@Autowired private JdbcTemplate jdbc;

	@Test
	void rejectionTimeoutReassignmentAndCompensationAreAtomicIdempotentAndAudited() {
		Order order = orders.save(Order.create(OrderId.newId(), Instant.parse("2026-01-01T00:00:00Z")));
		UUID correlationId = UUID.randomUUID();
		var confirmed = transition(order.id(), OrderStatus.CONFIRMED, "merchant", 0, "confirm", correlationId);

		assign(order.id(), UUID.randomUUID(), "decision-1", confirmed.version(), "assign-1", correlationId);
		var rejected = transition(order.id(), OrderStatus.ASSIGNMENT_REJECTED, "courier", 2,
				"reject-1", correlationId);
		var replay = transition(order.id(), OrderStatus.ASSIGNMENT_REJECTED, "courier", 2,
				"reject-1", correlationId);
		assertThat(replay.replayed()).isTrue();
		assertThat(replay.status()).isEqualTo(OrderStatus.ASSIGNMENT_REJECTED.name());

		var pending = transition(order.id(), OrderStatus.REASSIGNMENT_PENDING, "dispatch",
				rejected.version(), "reassign-1", correlationId);
		assign(order.id(), UUID.randomUUID(), "decision-2", pending.version(), "assign-2", correlationId);
		var timedOut = transition(order.id(), OrderStatus.ASSIGNMENT_TIMED_OUT, "system", 5,
				"timeout-1", correlationId);
		var pendingAgain = transition(order.id(), OrderStatus.REASSIGNMENT_PENDING, "dispatch",
				timedOut.version(), "reassign-2", correlationId);
		assign(order.id(), UUID.randomUUID(), "decision-3", pendingAgain.version(), "assign-3", correlationId);
		var compensating = transition(order.id(), OrderStatus.COMPENSATING, "customer", 8,
				"compensate-1", correlationId);
		var compensated = transition(order.id(), OrderStatus.COMPENSATED, "system", compensating.version(),
				"compensate-2", correlationId);
		var cancelled = transition(order.id(), OrderStatus.CANCELLED, "system", compensated.version(),
				"cancel-1", correlationId);

		assertThat(cancelled.status()).isEqualTo(OrderStatus.CANCELLED.name());
		assertThat(jdbc.queryForObject(
				"select count(*) from routemind.dispatch_assignment_leases where order_id = ? and state = 'COMMITTED'",
				Integer.class, order.id().value())).isZero();
		assertThat(jdbc.queryForObject(
				"select count(*) from routemind.dispatch_assignment_leases where order_id = ? and state = 'RELEASED'",
				Integer.class, order.id().value())).isEqualTo(3);
		assertThat(jdbc.queryForList(
				"select reason from routemind.dispatch_assignment_lease_events where order_id = ? and to_state = 'RELEASED'",
				String.class, order.id().value())).containsExactlyInAnyOrder(
						"fulfillment_assigned_to_assignment_rejected",
						"fulfillment_assigned_to_assignment_timed_out",
						"fulfillment_assigned_to_compensating");
		assertThat(jdbc.queryForObject(
				"select count(*) from routemind.order_command_idempotency where idempotency_key = 'reject-1'",
				Integer.class)).isOne();
		assertThat(jdbc.queryForObject(
				"select count(*) from routemind.order_transitions where order_id = ?", Integer.class,
				order.id().value())).isEqualTo(11);
		assertThat(jdbc.queryForObject(
				"select count(*) from routemind.outbox_messages where event_type like 'payment.%'",
				Integer.class)).isZero();
	}

	private OrderCommandResult transition(OrderId orderId, OrderStatus target, String actor,
			long expectedVersion, String key, UUID correlationId) {
		return commands.transitionCommand(orderId, target, actor, expectedVersion, correlationId,
				null, TRACE_ID, key);
	}

	private void assign(OrderId orderId, UUID courierId, String decisionId, long expectedVersion,
			String key, UUID correlationId) {
		assignments.apply(orderId, new DispatchAssignmentCommand(decisionId, "v1", courierId,
				"nearest", "1.0.0", ZERO_DIGEST, ONE_DIGEST, false, null, expectedVersion),
				correlationId, TRACE_ID, key);
	}
}
