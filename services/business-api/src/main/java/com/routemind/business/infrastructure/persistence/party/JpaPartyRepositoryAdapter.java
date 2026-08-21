package com.routemind.business.infrastructure.persistence.party;

import com.routemind.business.application.party.PartyRepository;
import com.routemind.business.domain.party.Party;
import com.routemind.business.domain.party.PartyId;
import java.util.Optional;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class JpaPartyRepositoryAdapter implements PartyRepository {

	private final SpringDataPartyRepository repository;

	public JpaPartyRepositoryAdapter(SpringDataPartyRepository repository) {
		this.repository = repository;
	}

	@Override
	@Transactional
	public Party save(Party party) {
		PartyEntity entity = repository.findById(party.id().value())
				.map(existing -> {
					existing.apply(party);
					return existing;
				})
				.orElseGet(() -> PartyEntity.from(party));
		return repository.saveAndFlush(entity).toDomain();
	}

	@Override
	@Transactional(readOnly = true)
	public Optional<Party> findById(PartyId id) {
		return repository.findById(id.value()).map(PartyEntity::toDomain);
	}
}
