package com.routemind.business.infrastructure.persistence.order;

import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface SpringDataOrderCommandIdempotencyRepository extends JpaRepository<OrderCommandIdempotencyEntity, String> {
	Optional<OrderCommandIdempotencyEntity> findByKeyAndTenantId(String key, UUID tenantId);
}
