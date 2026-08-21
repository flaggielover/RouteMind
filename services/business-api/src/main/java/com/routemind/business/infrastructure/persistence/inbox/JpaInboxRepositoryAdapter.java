package com.routemind.business.infrastructure.persistence.inbox;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.routemind.business.application.inbox.InboxRepository;
import com.routemind.business.domain.inbox.InboxMessage;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class JpaInboxRepositoryAdapter implements InboxRepository {

	private final SpringDataInboxRepository repository;
	private final ObjectMapper mapper;

	public JpaInboxRepositoryAdapter(SpringDataInboxRepository repository, ObjectMapper mapper) {
		this.repository = repository;
		this.mapper = mapper;
	}

	@Override
	@Transactional
	public InboxMessage save(InboxMessage message) {
		InboxEntity entity = repository.findById(message.eventId()).orElseGet(() ->
				InboxEntity.from(message, mapper));
		entity.apply(message, mapper);
		return repository.saveAndFlush(entity).toDomain(mapper);
	}

	@Override
	@Transactional(readOnly = true)
	public Optional<InboxMessage> findById(UUID eventId) {
		return repository.findById(eventId).map(entity -> entity.toDomain(mapper));
	}
}
