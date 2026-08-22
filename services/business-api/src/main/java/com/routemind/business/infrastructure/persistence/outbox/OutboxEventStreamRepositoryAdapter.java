package com.routemind.business.infrastructure.persistence.outbox;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.routemind.business.application.realtime.EventStreamEntry;
import com.routemind.business.application.realtime.EventStreamPage;
import com.routemind.business.application.realtime.EventStreamRepository;
import java.util.Collections;
import java.util.List;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class OutboxEventStreamRepositoryAdapter implements EventStreamRepository {

	private final SpringDataOutboxRepository repository;
	private final ObjectMapper mapper;

	public OutboxEventStreamRepositoryAdapter(SpringDataOutboxRepository repository, ObjectMapper mapper) {
		this.repository = repository;
		this.mapper = mapper;
	}

	@Override
	@Transactional(readOnly = true)
	public EventStreamPage recent(int limit) {
		if (limit < 1 || limit > 256) {
			throw new IllegalArgumentException("event stream repository limit must be between 1 and 256");
		}
		long total = repository.count();
		List<OutboxEntity> entities = repository
				.findByOrderByCreatedAtDescEventIdDesc(PageRequest.of(0, limit));
		Collections.reverse(entities);
		long oldest = entities.isEmpty() ? 0 : Math.max(1, total - entities.size() + 1);
		List<EventStreamEntry> entries = java.util.stream.IntStream.range(0, entities.size())
				.mapToObj(index -> new EventStreamEntry(oldest + index, entities.get(index).toDomain(mapper).event()))
				.toList();
		long newest = entries.isEmpty() ? 0 : entries.get(entries.size() - 1).cursor();
		return new EventStreamPage(oldest, newest, entries);
	}
}
