package com.routemind.business.application.outbox;

import com.routemind.business.application.security.TenantContext;
import com.routemind.business.domain.outbox.OutboxMessage;
import com.routemind.business.domain.security.TenantId;
import java.time.Clock;
import java.time.Instant;
import java.util.Objects;

public class OutboxRelay {

	private final OutboxRepository repository;
	private final EventPublisher publisher;
	private final Clock clock;
	private final TenantContext tenants;

	public OutboxRelay(OutboxRepository repository, EventPublisher publisher, Clock clock) {
		this(repository, publisher, clock, new TenantContext());
	}

	public OutboxRelay(OutboxRepository repository, EventPublisher publisher, Clock clock,
			TenantContext tenants) {
		this.repository = repository;
		this.publisher = publisher;
		this.clock = clock;
		this.tenants = Objects.requireNonNull(tenants, "tenants");
	}

	public int publishDue(int limit) {
		Instant now = clock.instant();
		int published = 0;
		for (OutboxMessage claimed : repository.claimDue(limit, now)) {
			try (TenantContext.Scope ignored = tenants.open(new TenantId(claimed.event().tenantId()))) {
				try {
					publisher.publish(claimed.event());
					repository.save(claimed.published(clock.instant()));
					published++;
				}
				catch (Exception exception) {
					repository.save(claimed.retry(clock.instant(), exception.getMessage()));
				}
			}
		}
		return published;
	}
}
