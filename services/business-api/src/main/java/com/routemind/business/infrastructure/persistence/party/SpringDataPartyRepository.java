package com.routemind.business.infrastructure.persistence.party;

import java.util.UUID;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

interface SpringDataPartyRepository extends JpaRepository<PartyEntity, UUID> {
	Optional<PartyEntity> findByIdAndTenantId(UUID id, UUID tenantId);

	List<PartyEntity> findAllByTenantId(UUID tenantId);
}
