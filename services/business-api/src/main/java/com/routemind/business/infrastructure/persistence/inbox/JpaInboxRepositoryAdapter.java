package com.routemind.business.infrastructure.persistence.inbox;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.routemind.business.application.inbox.InboxRepository;
import com.routemind.business.application.security.TenantContext;
import com.routemind.business.application.security.TenantIsolationException;
import com.routemind.business.domain.inbox.InboxMessage;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class JpaInboxRepositoryAdapter implements InboxRepository {

	private final SpringDataInboxRepository repository;
	private final ObjectMapper mapper;
	private final TenantContext tenants;

	public JpaInboxRepositoryAdapter(SpringDataInboxRepository repository, ObjectMapper mapper,
			TenantContext tenants) {
		this.repository = repository;
		this.mapper = mapper;
		this.tenants = tenants;
	}

	@Override
	@Transactional
	public InboxMessage save(InboxMessage message) {
		UUID tenantId = message.event().tenantId();
		if (!tenants.current().value().equals(tenantId)) {
			throw new TenantIsolationException();
		}
		InboxEntity entity = repository.findByEventIdAndTenantId(message.eventId(), tenantId).orElseGet(() -> {
			if (repository.existsById(message.eventId())) {
				throw new TenantIsolationException();
			}
			return InboxEntity.from(message, mapper);
		});
		entity.apply(message, mapper);
		return repository.saveAndFlush(entity).toDomain(mapper);
	}

	@Override
	@Transactional(readOnly = true)
	public Optional<InboxMessage> findById(UUID eventId) {
		return repository.findByEventIdAndTenantId(eventId, tenants.current().value())
				.map(entity -> entity.toDomain(mapper));
	}
}
