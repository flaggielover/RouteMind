package com.routemind.business.application.realtime;

import java.util.List;
import java.util.Objects;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class EventStreamService {

	public static final int MAX_BATCH_SIZE = 64;

	private final EventStreamRepository repository;

	public EventStreamService(EventStreamRepository repository) {
		this.repository = Objects.requireNonNull(repository, "repository");
	}

	@Transactional(readOnly = true)
	public List<EventStreamEntry> after(long cursor, int limit) {
		if (cursor < 0) {
			throw new IllegalArgumentException("event stream cursor must not be negative");
		}
		if (limit < 1 || limit > MAX_BATCH_SIZE) {
			throw new IllegalArgumentException("event stream limit must be between 1 and 64");
		}
		EventStreamPage page = repository.recent(MAX_BATCH_SIZE);
		if (page.entries().isEmpty()) {
			return List.of();
		}
		if (cursor > 0 && cursor < page.oldestCursor() - 1) {
			throw new EventStreamStaleException("event stream cursor is outside retention: " + cursor);
		}
		return page.entries().stream()
				.filter(entry -> entry.cursor() > cursor)
				.limit(limit)
				.toList();
	}
}
