package com.routemind.business.infrastructure.persistence.dispatch;

import com.routemind.business.application.dispatch.DispatchAssignmentLeaseConflictException;
import com.routemind.business.application.dispatch.DispatchAssignmentLeaseRepository;
import com.routemind.business.domain.dispatch.DispatchAssignmentLease;
import com.routemind.business.domain.dispatch.DispatchAssignmentLeaseState;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class JpaDispatchAssignmentLeaseRepository implements DispatchAssignmentLeaseRepository {

    private final SpringDataDispatchAssignmentLeaseRepository leases;
    private final SpringDataDispatchAssignmentLeaseEventRepository events;

    public JpaDispatchAssignmentLeaseRepository(SpringDataDispatchAssignmentLeaseRepository leases,
            SpringDataDispatchAssignmentLeaseEventRepository events) {
        this.leases = leases;
        this.events = events;
    }

    @Override
    @Transactional
    public DispatchAssignmentLease reserve(UUID orderId, UUID courierId, String decisionId, Instant now, Duration ttl) {
        Instant expiresAt = now.plus(ttl);
        DispatchAssignmentLeaseEntity existing = leases.findByCourierIdForUpdate(courierId).orElse(null);
        if (existing == null) {
            DispatchAssignmentLeaseEntity created = DispatchAssignmentLeaseEntity.create(orderId, courierId, decisionId,
                    1, UUID.randomUUID(), now, expiresAt);
            leases.saveAndFlush(created);
            events.save(DispatchAssignmentLeaseEventEntity.of(created, null, "reserve", now));
            return created.toDomain();
        }
        if (existing.state() == DispatchAssignmentLeaseState.COMMITTED) {
            if (existing.orderId().equals(orderId)) return existing.toDomain();
            throw new DispatchAssignmentLeaseConflictException("courier_already_assigned");
        }
        if (existing.state() == DispatchAssignmentLeaseState.PROVISIONALLY_RESERVED && existing.expiresAt().isAfter(now)) {
            if (existing.orderId().equals(orderId) && existing.decisionId().equals(decisionId)) return existing.toDomain();
            throw new DispatchAssignmentLeaseConflictException("courier_lease_conflict");
        }

        DispatchAssignmentLeaseState previous = existing.state();
        if (previous == DispatchAssignmentLeaseState.PROVISIONALLY_RESERVED) {
            existing.expire(existing.generation(), now);
            events.save(DispatchAssignmentLeaseEventEntity.of(existing, previous, "lease_timeout", now));
        }
        long generation = existing.generation() + 1;
        existing.replace(orderId, courierId, decisionId, generation, UUID.randomUUID(), now, expiresAt);
        leases.saveAndFlush(existing);
        events.save(DispatchAssignmentLeaseEventEntity.of(existing, previous, "reserve_after_" + previous.name().toLowerCase(), now));
        return existing.toDomain();
    }

    @Override
    @Transactional
    public DispatchAssignmentLease commit(UUID leaseId, long generation, String decisionId, Instant now) {
        DispatchAssignmentLeaseEntity lease = findForUpdate(leaseId);
        DispatchAssignmentLeaseState previous = lease.state();
        lease.commit(generation, decisionId, now);
        if (previous != lease.state()) {
            leases.saveAndFlush(lease);
            events.save(DispatchAssignmentLeaseEventEntity.of(lease, previous, "commit", now));
        }
        return lease.toDomain();
    }

    @Override
    @Transactional
    public DispatchAssignmentLease release(UUID leaseId, long generation, String decisionId, String reason, Instant now) {
        DispatchAssignmentLeaseEntity lease = findForUpdate(leaseId);
        DispatchAssignmentLeaseState previous = lease.state();
        lease.release(generation, decisionId, now);
        if (previous != lease.state()) {
            leases.saveAndFlush(lease);
            events.save(DispatchAssignmentLeaseEventEntity.of(lease, previous, requireReason(reason), now));
        }
        return lease.toDomain();
    }

    @Override
    @Transactional
    public DispatchAssignmentLease expire(UUID leaseId, long generation, String reason, Instant now) {
        DispatchAssignmentLeaseEntity lease = findForUpdate(leaseId);
        DispatchAssignmentLeaseState previous = lease.state();
        lease.expire(generation, now);
        if (previous != lease.state()) {
            leases.saveAndFlush(lease);
            events.save(DispatchAssignmentLeaseEventEntity.of(lease, previous, requireReason(reason), now));
        }
        return lease.toDomain();
    }

    @Override
    @Transactional
    public List<DispatchAssignmentLease> findCommittedByOrderId(UUID orderId) {
        return leases.findByOrderIdAndStateForUpdate(orderId, DispatchAssignmentLeaseState.COMMITTED)
                .stream().map(DispatchAssignmentLeaseEntity::toDomain).toList();
    }

    private DispatchAssignmentLeaseEntity findForUpdate(UUID leaseId) {
        return leases.findByLeaseId(leaseId).orElseThrow(() ->
                new DispatchAssignmentLeaseConflictException("lease_not_found"));
    }

    private static String requireReason(String reason) {
        if (reason == null || reason.isBlank() || reason.length() > 128) {
            throw new IllegalArgumentException("lease transition reason is invalid");
        }
        return reason;
    }
}
