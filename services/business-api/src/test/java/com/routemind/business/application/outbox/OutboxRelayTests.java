package com.routemind.business.application.outbox;

import static org.assertj.core.api.Assertions.assertThat;

import com.routemind.business.domain.event.EventEnvelope;
import com.routemind.business.domain.outbox.OutboxMessage;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class OutboxRelayTests {

	@Test
	void retriesFailureAndPublishesAfterConfirmation() {
		Instant now = Instant.parse("2026-01-01T00:00:00Z");
		var message = OutboxMessage.pending(event(now));
		var stored = new ArrayList<>(java.util.List.of(message));
		var publisherCalls = new ArrayList<UUID>();
		EventPublisher publisher = event -> {
			publisherCalls.add(event.eventId());
			if (publisherCalls.size() == 1) {
				throw new IllegalStateException("down");
			}
		};
		OutboxRepository repository = new OutboxRepository() {
			@Override public OutboxMessage save(OutboxMessage value) { stored.set(0, value); return value; }
			@Override public java.util.List<OutboxMessage> claimDue(int limit, Instant ignored) {
				OutboxMessage value = stored.get(0);
				if (value.status() == com.routemind.business.domain.outbox.OutboxStatus.PENDING
						|| value.status() == com.routemind.business.domain.outbox.OutboxStatus.RETRYABLE) {
					value = value.claim(now);
					stored.set(0, value);
					return java.util.List.of(value);
				}
				return java.util.List.of();
			}
			@Override public java.util.Optional<OutboxMessage> findById(UUID id) { return java.util.Optional.of(stored.get(0)); }
		};
		var relay = new OutboxRelay(repository, publisher, Clock.fixed(now, ZoneOffset.UTC));

		assertThat(relay.publishDue(1)).isZero();
		assertThat(stored.get(0).attempts()).isOne();
		var retryRelay = new OutboxRelay(repository, publisher,
				Clock.fixed(now.plusSeconds(2), ZoneOffset.UTC));
		assertThat(retryRelay.publishDue(1)).isOne();
		assertThat(stored.get(0).status()).isEqualTo(com.routemind.business.domain.outbox.OutboxStatus.PUBLISHED);
	}

	private static EventEnvelope event(Instant now) {
		return new EventEnvelope("1.0", UUID.randomUUID(), "order.status.changed", now, "business-api",
				UUID.randomUUID(), 1, UUID.randomUUID(), null, "0123456789abcdef0123456789abcdef", Map.of());
	}
}
