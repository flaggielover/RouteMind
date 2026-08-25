package com.routemind.business.infrastructure.persistence.party;

import com.routemind.business.application.party.PartyRepository;
import com.routemind.business.application.security.TenantContext;
import com.routemind.business.application.security.TenantIsolationException;
import com.routemind.business.domain.party.Party;
import com.routemind.business.domain.party.PartyId;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class JpaPartyRepositoryAdapter implements PartyRepository {

	private final SpringDataPartyRepository repository;
	private final TenantContext tenants;

	public JpaPartyRepositoryAdapter(SpringDataPartyRepository repository, TenantContext tenants) {
		this.repository = repository;
		this.tenants = tenants;
	}

	@Override
	@Transactional
	public Party save(Party party) {
		UUID tenantId = tenants.current().value();
		PartyEntity entity = repository.findByIdAndTenantId(party.id().value(), tenantId)
				.map(existing -> {
					existing.apply(party);
					return existing;
				})
				.orElseGet(() -> {
					if (repository.existsById(party.id().value())) throw new TenantIsolationException();
					return PartyEntity.from(party, tenantId);
				});
		return repository.saveAndFlush(entity).toDomain();
	}

	@Override
	@Transactional(readOnly = true)
	public Optional<Party> findById(PartyId id) {
		return repository.findByIdAndTenantId(id.value(), tenants.current().value()).map(PartyEntity::toDomain);
	}

	@Override
	@Transactional(readOnly = true)
	public List<Party> findAll() {
		return repository.findAllByTenantId(tenants.current().value()).stream().map(PartyEntity::toDomain).toList();
	}
}
