package com.routemind.business.application.outbox;

import com.routemind.business.domain.outbox.OutboxMessage;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface OutboxRepository {

	OutboxMessage save(OutboxMessage message);

	List<OutboxMessage> claimDue(int limit, Instant now);

	Optional<OutboxMessage> findById(UUID id);
}
