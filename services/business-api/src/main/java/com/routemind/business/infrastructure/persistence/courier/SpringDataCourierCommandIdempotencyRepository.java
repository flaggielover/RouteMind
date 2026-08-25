package com.routemind.business.infrastructure.persistence.courier;

import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface SpringDataCourierCommandIdempotencyRepository extends JpaRepository<CourierCommandIdempotencyEntity, String> {
	Optional<CourierCommandIdempotencyEntity> findByKeyAndTenantId(String key, UUID tenantId);
}
