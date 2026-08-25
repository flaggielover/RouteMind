package com.routemind.business.infrastructure.persistence.dispatch;

import com.routemind.business.application.dispatch.DispatchAssignmentLeaseConflictException;
import com.routemind.business.domain.dispatch.DispatchAssignmentLease;
import com.routemind.business.domain.dispatch.DispatchAssignmentLeaseState;
import com.routemind.business.infrastructure.persistence.TenantScopedEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "dispatch_assignment_leases", schema = "routemind")
class DispatchAssignmentLeaseEntity extends TenantScopedEntity {

    @Id
    @Column(name = "courier_id")
    private UUID courierId;

    @Column(name = "lease_id", nullable = false, unique = true)
    private UUID leaseId;

    @Column(name = "order_id", nullable = false)
    private UUID orderId;

    @Column(name = "decision_id", nullable = false, length = 128)
    private String decisionId;

    @Column(nullable = false)
    private long generation;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private DispatchAssignmentLeaseState state;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "expires_at", nullable = false)
    private Instant expiresAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    @Version
    @Column(nullable = false)
    private Long version;

    protected DispatchAssignmentLeaseEntity() {
    }

    static DispatchAssignmentLeaseEntity create(UUID orderId, UUID courierId, String decisionId,
            long generation, UUID leaseId, Instant createdAt, Instant expiresAt, UUID tenantId) {
        DispatchAssignmentLeaseEntity entity = new DispatchAssignmentLeaseEntity();
        entity.assignTenant(tenantId);
        entity.courierId = courierId;
        entity.leaseId = leaseId;
        entity.orderId = orderId;
        entity.decisionId = decisionId;
        entity.generation = generation;
        entity.state = DispatchAssignmentLeaseState.PROVISIONALLY_RESERVED;
        entity.createdAt = createdAt;
        entity.expiresAt = expiresAt;
        entity.updatedAt = createdAt;
        return entity;
    }

    void replace(UUID orderId, UUID courierId, String decisionId, long generation, UUID leaseId,
            Instant createdAt, Instant expiresAt) {
        this.courierId = courierId;
        this.leaseId = leaseId;
        this.orderId = orderId;
        this.decisionId = decisionId;
        this.generation = generation;
        this.state = DispatchAssignmentLeaseState.PROVISIONALLY_RESERVED;
        this.createdAt = createdAt;
        this.expiresAt = expiresAt;
        this.updatedAt = createdAt;
    }

    DispatchAssignmentLease toDomain() {
        return new DispatchAssignmentLease(leaseId, courierId, orderId, decisionId, generation, createdAt,
                expiresAt, state);
    }

    void commit(long expectedGeneration, String expectedDecisionId, Instant now) {
        validateLease(expectedGeneration, expectedDecisionId);
        if (state == DispatchAssignmentLeaseState.COMMITTED) return;
        if (state != DispatchAssignmentLeaseState.PROVISIONALLY_RESERVED) {
            throw new DispatchAssignmentLeaseConflictException("lease_not_active");
        }
        if (!expiresAt.isAfter(now)) throw new DispatchAssignmentLeaseConflictException("lease_expired");
        state = DispatchAssignmentLeaseState.COMMITTED;
        updatedAt = now;
    }

    void release(long expectedGeneration, String expectedDecisionId, Instant now) {
        validateLease(expectedGeneration, expectedDecisionId);
        if (state == DispatchAssignmentLeaseState.RELEASED) return;
        if (state != DispatchAssignmentLeaseState.PROVISIONALLY_RESERVED
                && state != DispatchAssignmentLeaseState.COMMITTED) {
            throw new DispatchAssignmentLeaseConflictException("lease_not_active");
        }
        state = DispatchAssignmentLeaseState.RELEASED;
        updatedAt = now;
    }

    void expire(long expectedGeneration, Instant now) {
        if (generation != expectedGeneration) throw new DispatchAssignmentLeaseConflictException("stale_lease_generation");
        if (state == DispatchAssignmentLeaseState.EXPIRED) return;
        if (state != DispatchAssignmentLeaseState.PROVISIONALLY_RESERVED) {
            throw new DispatchAssignmentLeaseConflictException("lease_not_active");
        }
        if (expiresAt.isAfter(now)) throw new DispatchAssignmentLeaseConflictException("lease_not_expired");
        state = DispatchAssignmentLeaseState.EXPIRED;
        updatedAt = now;
    }

    boolean matches(UUID expectedLeaseId) {
        return leaseId.equals(expectedLeaseId);
    }

    long generation() {
        return generation;
    }

    UUID leaseId() {
        return leaseId;
    }

    UUID courierId() {
        return courierId;
    }

    UUID orderId() {
        return orderId;
    }

    String decisionId() {
        return decisionId;
    }

    DispatchAssignmentLeaseState state() {
        return state;
    }

    Instant expiresAt() {
        return expiresAt;
    }

    private void validateLease(long expectedGeneration, String expectedDecisionId) {
        if (generation != expectedGeneration) throw new DispatchAssignmentLeaseConflictException("stale_lease_generation");
        if (!decisionId.equals(expectedDecisionId)) throw new DispatchAssignmentLeaseConflictException("lease_decision_mismatch");
    }
}
