package com.routemind.business.infrastructure.persistence.dispatch;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface SpringDataDispatchDecisionLedgerRepository extends JpaRepository<DispatchDecisionLedgerEntity, String> {
    Optional<DispatchDecisionLedgerEntity> findByDecisionIdAndTenantId(String decisionId, UUID tenantId);
    List<DispatchDecisionLedgerEntity> findAllByTenantIdOrderByCreatedAtDesc(UUID tenantId);
}
