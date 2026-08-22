package com.routemind.business.application.realtime;

import java.util.List;

public record EventStreamPage(long oldestCursor, long newestCursor, List<EventStreamEntry> entries) {

	public EventStreamPage {
		if (oldestCursor < 0 || newestCursor < 0 || newestCursor < oldestCursor) {
			throw new IllegalArgumentException("event stream cursor bounds are invalid");
		}
		entries = List.copyOf(entries);
	}
}
