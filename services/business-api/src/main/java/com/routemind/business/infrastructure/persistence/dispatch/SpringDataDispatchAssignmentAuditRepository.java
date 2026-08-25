package com.routemind.business.infrastructure.persistence.dispatch;

import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface SpringDataDispatchAssignmentAuditRepository extends JpaRepository<DispatchAssignmentAuditEntity, String> {
	Optional<DispatchAssignmentAuditEntity> findByIdempotencyKeyAndTenantId(String idempotencyKey, UUID tenantId);
}
