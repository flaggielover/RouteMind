package com.routemind.business.infrastructure.persistence.courier;

import org.springframework.data.jpa.repository.JpaRepository;

interface SpringDataCourierCommandIdempotencyRepository extends JpaRepository<CourierCommandIdempotencyEntity, String> {
}
