package com.routemind.business.application.order;

import static org.assertj.core.api.Assertions.assertThat;

import com.routemind.business.domain.order.Order;
import com.routemind.business.domain.order.OrderId;
import com.routemind.business.domain.order.OrderStatus;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class OrderCommandServiceTests {

	@Autowired private OrderRepository orders;
	@Autowired private OrderCommandService commands;
	@Autowired private JdbcTemplate jdbc;

	@BeforeEach
	void clear() {
		jdbc.update("delete from routemind.outbox_messages");
		jdbc.update("delete from routemind.orders");
	}

	@Test
	void writesOrderAndOutboxEventInOneApplicationCommand() {
		Order initial = Order.create(OrderId.newId(), Instant.parse("2026-01-01T00:00:00Z"));
		orders.save(initial);
		UUID correlationId = UUID.randomUUID();

		Order confirmed = commands.transition(initial.id(), OrderStatus.CONFIRMED, "customer", 0,
				correlationId, null, "0123456789abcdef0123456789abcdef");

		assertThat(confirmed.status()).isEqualTo(OrderStatus.CONFIRMED);
		assertThat(jdbc.queryForObject("select count(*) from routemind.orders where status = 'CONFIRMED'", Integer.class))
				.isOne();
		assertThat(jdbc.queryForObject("select count(*) from routemind.outbox_messages where correlation_id = ?",
					Integer.class, correlationId)).isOne();
	}
}
