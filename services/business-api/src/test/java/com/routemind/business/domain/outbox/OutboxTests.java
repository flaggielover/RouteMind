package com.routemind.business.domain.outbox;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalStateException;

import com.routemind.business.domain.event.EventEnvelope;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class OutboxTests {

	private static final Instant NOW = Instant.parse("2026-01-01T00:00:00Z");

	@Test
	void retainsStableEventIdentityAcrossRetryAndPublish() {
		EventEnvelope event = new EventEnvelope("1.0", UUID.randomUUID(), "order.status.changed", NOW,
				"business-api", UUID.randomUUID(), 1, UUID.randomUUID(), null,
				"0123456789abcdef0123456789abcdef", Map.of("status", "CONFIRMED"));
		OutboxMessage message = OutboxMessage.pending(event);
		OutboxMessage retry = message.claim(NOW).retry(NOW, "broker unavailable");
		OutboxMessage published = retry.claim(NOW.plusSeconds(2)).published(NOW.plusSeconds(3));

		assertThat(retry.id()).isEqualTo(event.eventId());
		assertThat(retry.attempts()).isOne();
		assertThat(published.status()).isEqualTo(OutboxStatus.PUBLISHED);
		assertThat(published.event().eventId()).isEqualTo(event.eventId());
	}

	@Test
	void onlyInFlightMessagesCanBeCompleted() {
		EventEnvelope event = new EventEnvelope("1.0", UUID.randomUUID(), "order.status.changed", NOW,
				"business-api", UUID.randomUUID(), 1, UUID.randomUUID(), null,
				"0123456789abcdef0123456789abcdef", Map.of());
		assertThatIllegalStateException().isThrownBy(() -> OutboxMessage.pending(event).published(NOW));
	}
}
