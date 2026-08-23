package com.routemind.business.infrastructure.persistence.dispatch;

import org.springframework.data.jpa.repository.JpaRepository;

interface SpringDataDispatchAssignmentAuditRepository extends JpaRepository<DispatchAssignmentAuditEntity, String> {
}
