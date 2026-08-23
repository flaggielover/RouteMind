package com.routemind.business.application.dispatch;

import com.routemind.business.domain.dispatch.DispatchAssignmentLease;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

public interface DispatchAssignmentLeaseRepository {

    DispatchAssignmentLease reserve(UUID orderId, UUID courierId, String decisionId, Instant now, Duration ttl);

    DispatchAssignmentLease commit(UUID leaseId, long generation, String decisionId, Instant now);

    DispatchAssignmentLease release(UUID leaseId, long generation, String decisionId, String reason, Instant now);

    DispatchAssignmentLease expire(UUID leaseId, long generation, String reason, Instant now);

    List<DispatchAssignmentLease> findCommittedByOrderId(UUID orderId);
}
