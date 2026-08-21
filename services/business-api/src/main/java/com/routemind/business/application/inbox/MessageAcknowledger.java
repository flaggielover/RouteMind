package com.routemind.business.application.inbox;

import java.util.UUID;

@FunctionalInterface
public interface MessageAcknowledger {

	void acknowledge(UUID eventId);
}
