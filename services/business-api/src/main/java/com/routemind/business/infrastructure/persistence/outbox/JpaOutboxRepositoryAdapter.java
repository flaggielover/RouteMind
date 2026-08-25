package com.routemind.business.infrastructure.persistence.outbox;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.routemind.business.application.outbox.OutboxRepository;
import com.routemind.business.application.security.TenantContext;
import com.routemind.business.application.security.TenantIsolationException;
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
	private final TenantContext tenants;

	public JpaOutboxRepositoryAdapter(SpringDataOutboxRepository repository, ObjectMapper mapper,
			TenantContext tenants) {
		this.repository = repository;
		this.mapper = mapper;
		this.tenants = tenants;
	}

	@Override
	@Transactional
	public OutboxMessage save(OutboxMessage message) {
		UUID tenantId = message.event().tenantId();
		if (!tenants.current().value().equals(tenantId)) {
			throw new TenantIsolationException();
		}
		OutboxEntity entity = repository.findByEventIdAndTenantId(message.id(), tenantId).orElseGet(() -> {
			if (repository.existsById(message.id())) {
				throw new TenantIsolationException();
			}
			return OutboxEntity.from(message, mapper);
		});
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
		return repository.findByEventIdAndTenantId(id, tenants.current().value())
				.map(entity -> entity.toDomain(mapper));
	}
}
