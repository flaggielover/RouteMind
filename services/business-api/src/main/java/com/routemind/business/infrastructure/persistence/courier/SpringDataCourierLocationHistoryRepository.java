package com.routemind.business.infrastructure.persistence.courier;

import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface SpringDataCourierLocationHistoryRepository extends JpaRepository<CourierLocationHistoryEntity, Long> {
	boolean existsByCourierIdAndSequence(UUID courierId, long sequence);

	long deleteByCourierIdAndSequenceLessThan(UUID courierId, long sequence);
}
