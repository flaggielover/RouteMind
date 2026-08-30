package com.routemind.business.infrastructure.persistence.dispatch;

import com.routemind.business.application.dispatch.DispatchDecisionLedgerRepository;
import com.routemind.business.application.security.TenantContext;
import com.routemind.business.domain.dispatch.DispatchDecisionLedger;
import com.routemind.business.infrastructure.persistence.TenantKey;
import java.util.List;
import java.util.Optional;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class JpaDispatchDecisionLedgerRepository implements DispatchDecisionLedgerRepository {

    private final SpringDataDispatchDecisionLedgerRepository repository;
    private final TenantContext tenants;

    public JpaDispatchDecisionLedgerRepository(SpringDataDispatchDecisionLedgerRepository repository,
            TenantContext tenants) {
        this.repository = repository;
        this.tenants = tenants;
    }

    @Override
    @Transactional
    public DispatchDecisionLedger save(DispatchDecisionLedger ledger) {
        var tenantId = tenants.current().value();
        String physicalId = TenantKey.encode(tenantId, ledger.decisionId());
        DispatchDecisionLedgerEntity entity = repository.findByDecisionIdAndTenantId(physicalId, tenantId)
                .orElseGet(() -> DispatchDecisionLedgerEntity.from(ledger, tenantId));
        entity.apply(ledger);
        return repository.saveAndFlush(entity).toDomain();
    }

    @Override
    @Transactional(readOnly = true)
    public Optional<DispatchDecisionLedger> findByDecisionId(String decisionId) {
        var tenantId = tenants.current().value();
        return repository.findByDecisionIdAndTenantId(TenantKey.encode(tenantId, decisionId), tenantId)
                .map(DispatchDecisionLedgerEntity::toDomain);
    }

    @Override
    @Transactional(readOnly = true)
    public List<DispatchDecisionLedger> findAll() {
        var tenantId = tenants.current().value();
        return repository.findAllByTenantIdOrderByCreatedAtDesc(tenantId).stream()
                .map(DispatchDecisionLedgerEntity::toDomain)
                .toList();
    }
}
