package com.routemind.business.infrastructure.persistence.order;

import java.util.UUID;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

interface SpringDataOrderRepository extends JpaRepository<OrderEntity, UUID> {
	Optional<OrderEntity> findByIdAndTenantId(UUID id, UUID tenantId);

	List<OrderEntity> findAllByTenantId(UUID tenantId);
}
