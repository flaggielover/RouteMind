package com.routemind.business.infrastructure.persistence.outbox;

import static org.assertj.core.api.Assertions.assertThat;

import com.routemind.business.domain.event.EventEnvelope;
import com.routemind.business.domain.outbox.OutboxMessage;
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
class OutboxRepositoryTests {

	@Autowired private JpaOutboxRepositoryAdapter outbox;
	@Autowired private JdbcTemplate jdbc;

	@BeforeEach
	void clear() {
		jdbc.update("delete from routemind.outbox_messages");
	}

	@Test
	void roundTripsEnvelopeAndClaimsPendingMessage() {
		Instant now = Instant.parse("2026-01-01T00:00:00Z");
		EventEnvelope event = new EventEnvelope("1.0", UUID.randomUUID(), "order.status.changed", now,
				"business-api", UUID.randomUUID(), 1, UUID.randomUUID(), null,
				"0123456789abcdef0123456789abcdef", Map.of("status", "CONFIRMED"));
		outbox.save(OutboxMessage.pending(event));

		var claimed = outbox.claimDue(10, now);
		assertThat(claimed).hasSize(1);
		assertThat(claimed.get(0).status()).isEqualTo(com.routemind.business.domain.outbox.OutboxStatus.IN_FLIGHT);
		assertThat(outbox.findById(event.eventId()).orElseThrow().event().payload())
				.containsEntry("status", "CONFIRMED");
	}
}
