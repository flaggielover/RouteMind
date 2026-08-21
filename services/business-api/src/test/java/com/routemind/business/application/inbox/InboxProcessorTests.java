package com.routemind.business.application.inbox;

import static org.assertj.core.api.Assertions.assertThat;

import com.routemind.business.domain.event.EventEnvelope;
import com.routemind.business.domain.inbox.InboxMessage;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

class InboxProcessorTests {

	@Test
	void processesOnceAndAcknowledgesDuplicatesWithoutReinvokingHandler() {
		Instant now = Instant.parse("2026-01-01T00:00:00Z");
		EventEnvelope event = new EventEnvelope("1.0", UUID.randomUUID(), "order.status.changed", now,
				"business-api", UUID.randomUUID(), 1, UUID.randomUUID(), null,
				"0123456789abcdef0123456789abcdef", Map.of());
		var stored = new java.util.HashMap<UUID, InboxMessage>();
		InboxRepository repository = new InboxRepository() {
			@Override public InboxMessage save(InboxMessage value) { stored.put(value.eventId(), value); return value; }
			@Override public java.util.Optional<InboxMessage> findById(UUID id) { return java.util.Optional.ofNullable(stored.get(id)); }
		};
		var handlerCalls = new AtomicInteger();
		var acknowledgements = new AtomicInteger();
		var processor = new InboxProcessor(repository, Clock.fixed(now, ZoneOffset.UTC), 3);

		assertThat(processor.process(event, ignored -> handlerCalls.incrementAndGet(), ignored -> acknowledgements.incrementAndGet())).isTrue();
		assertThat(processor.process(event, ignored -> handlerCalls.incrementAndGet(), ignored -> acknowledgements.incrementAndGet())).isFalse();
		assertThat(handlerCalls).hasValue(1);
		assertThat(acknowledgements).hasValue(2);
	}
}
