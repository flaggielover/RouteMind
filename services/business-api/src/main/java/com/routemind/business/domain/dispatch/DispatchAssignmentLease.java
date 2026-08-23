package com.routemind.business.domain.dispatch;

import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

public record DispatchAssignmentLease(UUID leaseId, UUID courierId, UUID orderId, String decisionId,
        long generation, Instant createdAt, Instant expiresAt, DispatchAssignmentLeaseState state) {

    public DispatchAssignmentLease {
        Objects.requireNonNull(leaseId, "leaseId");
        Objects.requireNonNull(courierId, "courierId");
        Objects.requireNonNull(orderId, "orderId");
        if (decisionId == null || decisionId.isBlank() || decisionId.length() > 128) {
            throw new IllegalArgumentException("decisionId is invalid");
        }
        if (generation < 1) throw new IllegalArgumentException("generation must be positive");
        Objects.requireNonNull(createdAt, "createdAt");
        Objects.requireNonNull(expiresAt, "expiresAt");
        if (!expiresAt.isAfter(createdAt)) throw new IllegalArgumentException("expiresAt must be after createdAt");
        Objects.requireNonNull(state, "state");
    }

    public boolean activeAt(Instant now) {
        Objects.requireNonNull(now, "now");
        return state == DispatchAssignmentLeaseState.PROVISIONALLY_RESERVED && expiresAt.isAfter(now);
    }
}
