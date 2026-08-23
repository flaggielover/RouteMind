package com.routemind.business.application.dispatch;

import com.routemind.business.domain.dispatch.DispatchAssignmentLease;
import java.time.Clock;
import java.time.Duration;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public final class DispatchAssignmentLeaseService {

    static final Duration DEFAULT_TTL = Duration.ofSeconds(30);

    private final DispatchAssignmentLeaseRepository leases;
    private final Clock clock;
    private final Duration ttl;

    @Autowired
    public DispatchAssignmentLeaseService(DispatchAssignmentLeaseRepository leases, Clock clock) {
        this(leases, clock, DEFAULT_TTL);
    }

    DispatchAssignmentLeaseService(DispatchAssignmentLeaseRepository leases, Clock clock, Duration ttl) {
        if (ttl.isNegative() || ttl.isZero()) throw new IllegalArgumentException("lease ttl must be positive");
        this.leases = leases;
        this.clock = clock;
        this.ttl = ttl;
    }

    public DispatchAssignmentLease reserve(UUID orderId, UUID courierId, String decisionId) {
        return leases.reserve(orderId, courierId, decisionId, clock.instant(), ttl);
    }

    public DispatchAssignmentLease commit(DispatchAssignmentLease lease) {
        return leases.commit(lease.leaseId(), lease.generation(), lease.decisionId(), clock.instant());
    }

    public DispatchAssignmentLease release(DispatchAssignmentLease lease, String reason) {
        return leases.release(lease.leaseId(), lease.generation(), lease.decisionId(), reason, clock.instant());
    }

    public DispatchAssignmentLease expire(DispatchAssignmentLease lease, String reason) {
        return leases.expire(lease.leaseId(), lease.generation(), reason, clock.instant());
    }
}
