package com.routemind.business.domain.dispatch;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class DispatchAssignmentLeaseTests {

    private static final Instant CREATED_AT = Instant.parse("2026-08-23T00:00:00Z");

    @Test
    void activeWindowIsExplicitAndExpiresAtTheBoundary() {
        DispatchAssignmentLease lease = new DispatchAssignmentLease(UUID.randomUUID(), UUID.randomUUID(),
                UUID.randomUUID(), "decision-1", 3, CREATED_AT, CREATED_AT.plusSeconds(30),
                DispatchAssignmentLeaseState.PROVISIONALLY_RESERVED);

        assertThat(lease.activeAt(CREATED_AT.plusSeconds(29))).isTrue();
        assertThat(lease.activeAt(CREATED_AT.plusSeconds(30))).isFalse();
    }

    @Test
    void generationChangesWhenAReservationIsReplaced() {
        DispatchAssignmentLease first = new DispatchAssignmentLease(UUID.randomUUID(), UUID.randomUUID(),
                UUID.randomUUID(), "decision-1", 1, CREATED_AT, CREATED_AT.plusSeconds(30),
                DispatchAssignmentLeaseState.PROVISIONALLY_RESERVED);
        DispatchAssignmentLease second = new DispatchAssignmentLease(UUID.randomUUID(), first.courierId(),
                first.orderId(), "decision-2", first.generation() + 1, CREATED_AT.plusSeconds(31),
                CREATED_AT.plusSeconds(61), DispatchAssignmentLeaseState.PROVISIONALLY_RESERVED);

        assertThat(second.generation()).isGreaterThan(first.generation());
        assertThat(second.leaseId()).isNotEqualTo(first.leaseId());
    }
}
