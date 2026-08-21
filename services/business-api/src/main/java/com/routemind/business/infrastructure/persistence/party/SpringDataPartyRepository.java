package com.routemind.business.infrastructure.persistence.party;

import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface SpringDataPartyRepository extends JpaRepository<PartyEntity, UUID> {
}
