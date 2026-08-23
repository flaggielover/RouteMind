package com.routemind.business.infrastructure.persistence.dispatch;

import org.springframework.data.jpa.repository.JpaRepository;

interface SpringDataDispatchAssignmentLeaseEventRepository extends JpaRepository<DispatchAssignmentLeaseEventEntity, Long> {
}
