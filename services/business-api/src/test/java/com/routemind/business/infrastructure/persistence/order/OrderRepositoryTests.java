package com.routemind.business.infrastructure.persistence.order;

import static org.assertj.core.api.Assertions.assertThat;

import com.routemind.business.domain.order.Order;
import com.routemind.business.domain.order.OrderId;
import com.routemind.business.domain.order.OrderStatus;
import java.time.Instant;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class OrderRepositoryTests {

	@Autowired
	private JpaOrderRepositoryAdapter orders;

	@Autowired
	private JdbcTemplate jdbc;

	@BeforeEach
	void clearTables() {
		jdbc.update("delete from routemind.orders");
	}

	@Test
	void persistsLifecycleAndTransitionAudit() {
		Instant t0 = Instant.parse("2026-01-01T00:00:00Z");
		Order created = Order.create(OrderId.newId(), t0);
		Order confirmed = created.transitionTo(OrderStatus.CONFIRMED, "customer", t0.plusSeconds(1), 0);
		Order saved = orders.save(confirmed);

		Order loaded = orders.findById(saved.id()).orElseThrow();
		assertThat(loaded.status()).isEqualTo(OrderStatus.CONFIRMED);
		assertThat(loaded.version()).isEqualTo(0);
		assertThat(loaded.transitions()).hasSize(1);
		assertThat(jdbc.queryForObject("select count(*) from routemind.order_transitions", Integer.class))
				.isOne();
	}

}
