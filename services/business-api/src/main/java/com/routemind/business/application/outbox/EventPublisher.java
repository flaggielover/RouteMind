package com.routemind.business.application.outbox;

import com.routemind.business.domain.event.EventEnvelope;

@FunctionalInterface
public interface EventPublisher {

	void publish(EventEnvelope event) throws Exception;
}
