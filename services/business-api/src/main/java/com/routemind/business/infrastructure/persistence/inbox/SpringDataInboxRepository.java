package com.routemind.business.infrastructure.persistence.inbox;

import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface SpringDataInboxRepository extends JpaRepository<InboxEntity, UUID> {
}
