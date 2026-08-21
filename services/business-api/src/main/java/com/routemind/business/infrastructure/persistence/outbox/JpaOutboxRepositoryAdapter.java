package com.routemind.business.infrastructure.persistence.outbox;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.routemind.business.application.outbox.OutboxRepository;
import com.routemind.business.domain.outbox.OutboxMessage;
import com.routemind.business.domain.outbox.OutboxStatus;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class JpaOutboxRepositoryAdapter implements OutboxRepository {

	private final SpringDataOutboxRepository repository;
	private final ObjectMapper mapper;

	public JpaOutboxRepositoryAdapter(SpringDataOutboxRepository repository, ObjectMapper mapper) {
		this.repository = repository;
		this.mapper = mapper;
	}

	@Override
	@Transactional
	public OutboxMessage save(OutboxMessage message) {
		OutboxEntity entity = repository.findById(message.id()).orElseGet(() ->
				OutboxEntity.from(message, mapper));
		entity.apply(message, mapper);
		return repository.saveAndFlush(entity).toDomain(mapper);
	}

	@Override
	@Transactional
	public List<OutboxMessage> claimDue(int limit, Instant now) {
		if (limit < 1) {
			throw new IllegalArgumentException("limit must be positive");
		}
		return repository.findByStatusInAndNextAttemptAtLessThanEqualOrderByCreatedAtAsc(
				List.of(OutboxStatus.PENDING, OutboxStatus.RETRYABLE), now, PageRequest.of(0, limit))
				.stream().<OutboxMessage>map(entity -> {
					OutboxMessage claimed = entity.toDomain(mapper).claim(now);
					entity.apply(claimed, mapper);
					return entity.toDomain(mapper);
				}).toList();
	}

	@Override
	@Transactional(readOnly = true)
	public Optional<OutboxMessage> findById(UUID id) {
		return repository.findById(id).map(entity -> entity.toDomain(mapper));
	}
}
