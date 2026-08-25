package com.routemind.business.infrastructure.persistence.dispatch;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.routemind.business.application.dispatch.DispatchAssignmentLeaseConflictException;
import com.routemind.business.domain.dispatch.DispatchAssignmentLeaseState;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class DispatchAssignmentLeaseEntityTests {

    private static final Instant CREATED_AT = Instant.parse("2026-08-23T00:00:00Z");

    @Test
    void duplicateCommitIsIdempotentButStaleGenerationIsRejected() {
        DispatchAssignmentLeaseEntity lease = lease();
        lease.commit(1, "decision-1", CREATED_AT.plusSeconds(1));
        lease.commit(1, "decision-1", CREATED_AT.plusSeconds(2));

        assertThat(lease.state()).isEqualTo(DispatchAssignmentLeaseState.COMMITTED);
        assertThatThrownBy(() -> lease.commit(2, "decision-1", CREATED_AT.plusSeconds(2)))
                .isInstanceOf(DispatchAssignmentLeaseConflictException.class)
                .hasMessage("stale_lease_generation");
    }

    @Test
    void expiryAndReleaseAreBoundedAndCannotCommitAfterwards() {
        DispatchAssignmentLeaseEntity lease = lease();
        assertThatThrownBy(() -> lease.expire(1, CREATED_AT.plusSeconds(29)))
                .isInstanceOf(DispatchAssignmentLeaseConflictException.class)
                .hasMessage("lease_not_expired");

        lease.expire(1, CREATED_AT.plusSeconds(30));
        assertThat(lease.state()).isEqualTo(DispatchAssignmentLeaseState.EXPIRED);
        assertThatThrownBy(() -> lease.commit(1, "decision-1", CREATED_AT.plusSeconds(31)))
                .isInstanceOf(DispatchAssignmentLeaseConflictException.class)
                .hasMessage("lease_not_active");

        DispatchAssignmentLeaseEntity released = lease();
        released.release(1, "decision-1", CREATED_AT.plusSeconds(1));
        released.release(1, "decision-1", CREATED_AT.plusSeconds(2));
        assertThat(released.state()).isEqualTo(DispatchAssignmentLeaseState.RELEASED);
    }

    private static DispatchAssignmentLeaseEntity lease() {
        return DispatchAssignmentLeaseEntity.create(UUID.randomUUID(), UUID.randomUUID(), "decision-1", 1,
                UUID.randomUUID(), CREATED_AT, CREATED_AT.plusSeconds(30),
                com.routemind.business.domain.security.TenantId.LEGACY.value());
    }
}
