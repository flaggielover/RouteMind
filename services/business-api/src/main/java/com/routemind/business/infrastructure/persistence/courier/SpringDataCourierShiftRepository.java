package com.routemind.business.infrastructure.persistence.courier;

import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface SpringDataCourierShiftRepository extends JpaRepository<CourierShiftEntity, UUID> {
}
