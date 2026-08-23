package com.routemind.business.infrastructure.persistence.dispatch;

import com.routemind.business.application.dispatch.DispatchDecisionLedgerRepository;
import com.routemind.business.domain.dispatch.DispatchDecisionLedger;
import java.util.Optional;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class JpaDispatchDecisionLedgerRepository implements DispatchDecisionLedgerRepository {

    private final SpringDataDispatchDecisionLedgerRepository repository;

    public JpaDispatchDecisionLedgerRepository(SpringDataDispatchDecisionLedgerRepository repository) {
        this.repository = repository;
    }

    @Override
    @Transactional
    public DispatchDecisionLedger save(DispatchDecisionLedger ledger) {
        DispatchDecisionLedgerEntity entity = repository.findById(ledger.decisionId())
                .orElseGet(() -> DispatchDecisionLedgerEntity.from(ledger));
        entity.apply(ledger);
        return repository.saveAndFlush(entity).toDomain();
    }

    @Override
    @Transactional(readOnly = true)
    public Optional<DispatchDecisionLedger> findByDecisionId(String decisionId) {
        return repository.findByDecisionId(decisionId).map(DispatchDecisionLedgerEntity::toDomain);
    }
}
