package com.routemind.business.infrastructure.persistence.inbox;

import static org.assertj.core.api.Assertions.assertThat;

import com.routemind.business.domain.event.EventEnvelope;
import com.routemind.business.domain.inbox.InboxMessage;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class InboxRepositoryTests {

	@Autowired private JpaInboxRepositoryAdapter inbox;
	@Autowired private JdbcTemplate jdbc;

	@BeforeEach
	void clear() {
		jdbc.update("delete from routemind.inbox_messages");
	}

	@Test
	void roundTripsEventIdentityAndProcessingState() {
		Instant now = Instant.parse("2026-01-01T00:00:00Z");
		EventEnvelope event = new EventEnvelope("1.0", UUID.randomUUID(), "order.status.changed", now,
				"business-api", UUID.randomUUID(), 1, UUID.randomUUID(), null,
				"0123456789abcdef0123456789abcdef", Map.of("status", "CONFIRMED"));
		inbox.save(InboxMessage.received(event, now).claim(now));
		inbox.save(inbox.findById(event.eventId()).orElseThrow().processed(now.plusSeconds(1)));

		assertThat(inbox.findById(event.eventId()).orElseThrow().status())
				.isEqualTo(com.routemind.business.domain.inbox.InboxStatus.PROCESSED);
		assertThat(jdbc.queryForObject("select count(*) from routemind.inbox_messages", Integer.class)).isOne();
	}
}
