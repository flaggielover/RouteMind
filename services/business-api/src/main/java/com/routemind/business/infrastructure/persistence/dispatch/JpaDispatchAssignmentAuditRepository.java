package com.routemind.business.infrastructure.persistence.dispatch;

import com.routemind.business.application.dispatch.DispatchAssignmentAuditRepository;
import com.routemind.business.domain.dispatch.DispatchAssignmentAudit;
import java.util.Optional;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class JpaDispatchAssignmentAuditRepository implements DispatchAssignmentAuditRepository {

    private final SpringDataDispatchAssignmentAuditRepository repository;

    public JpaDispatchAssignmentAuditRepository(SpringDataDispatchAssignmentAuditRepository repository) {
        this.repository = repository;
    }

    @Override
    @Transactional
    public DispatchAssignmentAudit save(DispatchAssignmentAudit audit) {
        DispatchAssignmentAuditEntity entity = repository.findById(audit.idempotencyKey())
                .orElseGet(() -> DispatchAssignmentAuditEntity.from(audit));
        entity.apply(audit);
        return repository.saveAndFlush(entity).toDomain();
    }

    @Override
    @Transactional(readOnly = true)
    public Optional<DispatchAssignmentAudit> findByIdempotencyKey(String idempotencyKey) {
        return repository.findById(idempotencyKey).map(DispatchAssignmentAuditEntity::toDomain);
    }
}
