package com.routemind.business.application.inbox;

import com.routemind.business.domain.event.EventEnvelope;
import com.routemind.business.domain.inbox.InboxMessage;
import com.routemind.business.domain.inbox.InboxStatus;
import com.routemind.business.application.security.TenantContext;
import java.time.Clock;
import java.time.Instant;
import java.util.UUID;
import java.util.function.Consumer;

public class InboxProcessor {

	private final InboxRepository repository;
	private final Clock clock;
	private final int maxAttempts;
	private final TenantContext tenants;

	public InboxProcessor(InboxRepository repository, Clock clock, int maxAttempts) {
		this(repository, clock, maxAttempts, new TenantContext());
	}

	public InboxProcessor(InboxRepository repository, Clock clock, int maxAttempts, TenantContext tenants) {
		this.repository = repository;
		this.clock = clock;
		if (maxAttempts < 1) {
			throw new IllegalArgumentException("maxAttempts must be positive");
		}
		this.maxAttempts = maxAttempts;
		this.tenants = java.util.Objects.requireNonNull(tenants, "tenants");
	}

	public boolean process(EventEnvelope event, Consumer<EventEnvelope> handler,
			MessageAcknowledger acknowledger) {
		try (TenantContext.Scope ignored = tenants.open(new com.routemind.business.domain.security.TenantId(
				event.tenantId()))) {
			return processInTenant(event, handler, acknowledger);
		}
	}

	private boolean processInTenant(EventEnvelope event, Consumer<EventEnvelope> handler,
			MessageAcknowledger acknowledger) {
		Instant now = clock.instant();
		InboxMessage current = repository.findById(event.eventId()).orElse(null);
		if (current != null && (current.status() == InboxStatus.PROCESSED
				|| current.status() == InboxStatus.DEAD_LETTER)) {
			acknowledger.acknowledge(event.eventId());
			return false;
		}
		InboxMessage claimed = (current == null ? InboxMessage.received(event, now) : current).claim(now);
		repository.save(claimed);
		try {
			handler.accept(event);
			repository.save(claimed.processed(clock.instant()));
			acknowledger.acknowledge(event.eventId());
			return true;
		} catch (RuntimeException exception) {
			repository.save(claimed.failed(clock.instant(), exception.getMessage(), maxAttempts));
			acknowledger.acknowledge(event.eventId());
			return false;
		}
	}
}
