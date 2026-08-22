package com.routemind.business.infrastructure.persistence.order;

import org.springframework.data.jpa.repository.JpaRepository;

interface SpringDataOrderCommandIdempotencyRepository extends JpaRepository<OrderCommandIdempotencyEntity, String> {
}
