package com.routemind.business.application.inbox;

import com.routemind.business.domain.inbox.InboxMessage;
import java.util.Optional;
import java.util.UUID;

public interface InboxRepository {

	InboxMessage save(InboxMessage message);

	Optional<InboxMessage> findById(UUID eventId);
}
