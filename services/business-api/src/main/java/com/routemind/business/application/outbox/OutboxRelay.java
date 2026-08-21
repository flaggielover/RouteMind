package com.routemind.business.application.outbox;

import com.routemind.business.domain.outbox.OutboxMessage;
import java.time.Clock;
import java.time.Instant;

public class OutboxRelay {

	private final OutboxRepository repository;
	private final EventPublisher publisher;
	private final Clock clock;

	public OutboxRelay(OutboxRepository repository, EventPublisher publisher, Clock clock) {
		this.repository = repository;
		this.publisher = publisher;
		this.clock = clock;
	}

	public int publishDue(int limit) {
		Instant now = clock.instant();
		int published = 0;
		for (OutboxMessage claimed : repository.claimDue(limit, now)) {
			try {
				publisher.publish(claimed.event());
				repository.save(claimed.published(clock.instant()));
				published++;
			} catch (Exception exception) {
				repository.save(claimed.retry(clock.instant(), exception.getMessage()));
			}
		}
		return published;
	}
}
