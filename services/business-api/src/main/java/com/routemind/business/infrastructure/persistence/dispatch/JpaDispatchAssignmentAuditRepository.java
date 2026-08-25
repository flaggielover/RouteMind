package com.routemind.business.infrastructure.persistence.dispatch;

import com.routemind.business.application.dispatch.DispatchAssignmentAuditRepository;
import com.routemind.business.application.security.TenantContext;
import com.routemind.business.domain.dispatch.DispatchAssignmentAudit;
import com.routemind.business.infrastructure.persistence.TenantKey;
import java.util.Optional;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class JpaDispatchAssignmentAuditRepository implements DispatchAssignmentAuditRepository {

    private final SpringDataDispatchAssignmentAuditRepository repository;
    private final TenantContext tenants;

    public JpaDispatchAssignmentAuditRepository(SpringDataDispatchAssignmentAuditRepository repository,
            TenantContext tenants) {
        this.repository = repository;
        this.tenants = tenants;
    }

    @Override
    @Transactional
    public DispatchAssignmentAudit save(DispatchAssignmentAudit audit) {
        var tenantId = tenants.current().value();
        String physicalKey = TenantKey.encode(tenantId, audit.idempotencyKey());
        DispatchAssignmentAuditEntity entity = repository.findByIdempotencyKeyAndTenantId(physicalKey, tenantId)
                .orElseGet(() -> DispatchAssignmentAuditEntity.from(audit, tenantId));
        entity.apply(audit);
        return repository.saveAndFlush(entity).toDomain();
    }

    @Override
    @Transactional(readOnly = true)
    public Optional<DispatchAssignmentAudit> findByIdempotencyKey(String idempotencyKey) {
        var tenantId = tenants.current().value();
        return repository.findByIdempotencyKeyAndTenantId(TenantKey.encode(tenantId, idempotencyKey), tenantId)
                .map(DispatchAssignmentAuditEntity::toDomain);
    }
}
