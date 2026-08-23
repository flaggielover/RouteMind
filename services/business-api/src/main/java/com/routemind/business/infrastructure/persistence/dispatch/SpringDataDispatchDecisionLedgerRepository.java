package com.routemind.business.infrastructure.persistence.dispatch;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

interface SpringDataDispatchDecisionLedgerRepository extends JpaRepository<DispatchDecisionLedgerEntity, String> {
    Optional<DispatchDecisionLedgerEntity> findByDecisionId(String decisionId);
}
