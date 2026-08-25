package com.routemind.business.infrastructure.persistence.courier;

import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface SpringDataCourierLocationHistoryRepository extends JpaRepository<CourierLocationHistoryEntity, Long> {
	boolean existsByCourierIdAndSequenceAndTenantId(UUID courierId, long sequence, UUID tenantId);

	long deleteByCourierIdAndSequenceLessThanAndTenantId(UUID courierId, long sequence, UUID tenantId);
}
