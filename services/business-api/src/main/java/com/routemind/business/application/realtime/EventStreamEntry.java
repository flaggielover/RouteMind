package com.routemind.business.application.realtime;

import com.routemind.business.domain.event.EventEnvelope;
import java.util.Objects;

public record EventStreamEntry(long cursor, EventEnvelope event) {

	public EventStreamEntry {
		if (cursor < 1) {
			throw new IllegalArgumentException("event stream cursor must be positive");
		}
		Objects.requireNonNull(event, "event");
	}
}
