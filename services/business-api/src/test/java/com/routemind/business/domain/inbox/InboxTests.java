package com.routemind.business.domain.inbox;

import static org.assertj.core.api.Assertions.assertThat;

import com.routemind.business.domain.event.EventEnvelope;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class InboxTests {

	@Test
	void poisonMessageMovesToDeadLetterAfterBoundedAttempts() {
		Instant now = Instant.parse("2026-01-01T00:00:00Z");
		EventEnvelope event = new EventEnvelope("1.0", UUID.randomUUID(), "order.status.changed", now,
				"business-api", UUID.randomUUID(), 1, UUID.randomUUID(), null,
				"0123456789abcdef0123456789abcdef", Map.of());
		InboxMessage message = InboxMessage.received(event, now);
		message = message.claim(now).failed(now, "bad payload", 2);
		message = message.claim(now.plusSeconds(2)).failed(now.plusSeconds(2), "bad payload", 2);

		assertThat(message.status()).isEqualTo(InboxStatus.DEAD_LETTER);
		assertThat(message.attempts()).isEqualTo(2);
	}
}
