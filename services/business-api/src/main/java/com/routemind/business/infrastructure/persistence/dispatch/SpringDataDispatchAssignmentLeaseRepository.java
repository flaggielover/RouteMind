package com.routemind.business.infrastructure.persistence.dispatch;

import com.routemind.business.domain.dispatch.DispatchAssignmentLeaseState;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import jakarta.persistence.LockModeType;

interface SpringDataDispatchAssignmentLeaseRepository extends JpaRepository<DispatchAssignmentLeaseEntity, UUID> {

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select lease from DispatchAssignmentLeaseEntity lease where lease.courierId = :courierId")
    Optional<DispatchAssignmentLeaseEntity> findByCourierIdForUpdate(UUID courierId);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    Optional<DispatchAssignmentLeaseEntity> findByLeaseId(UUID leaseId);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select lease from DispatchAssignmentLeaseEntity lease where lease.orderId = :orderId and lease.state = :state")
    List<DispatchAssignmentLeaseEntity> findByOrderIdAndStateForUpdate(UUID orderId,
            DispatchAssignmentLeaseState state);
}
