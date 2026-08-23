package com.routemind.business.infrastructure.persistence.dispatch;

import com.routemind.business.domain.dispatch.DispatchAssignmentLeaseState;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "dispatch_assignment_lease_events", schema = "routemind")
class DispatchAssignmentLeaseEventEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "lease_id", nullable = false)
    private UUID leaseId;

    @Column(name = "courier_id", nullable = false)
    private UUID courierId;

    @Column(name = "order_id", nullable = false)
    private UUID orderId;

    @Column(name = "decision_id", nullable = false, length = 128)
    private String decisionId;

    @Column(nullable = false)
    private long generation;

    @Enumerated(EnumType.STRING)
    @Column(name = "from_state", length = 32)
    private DispatchAssignmentLeaseState fromState;

    @Enumerated(EnumType.STRING)
    @Column(name = "to_state", nullable = false, length = 32)
    private DispatchAssignmentLeaseState toState;

    @Column(nullable = false, length = 128)
    private String reason;

    @Column(name = "occurred_at", nullable = false)
    private Instant occurredAt;

    protected DispatchAssignmentLeaseEventEntity() {
    }

    static DispatchAssignmentLeaseEventEntity of(DispatchAssignmentLeaseEntity lease,
            DispatchAssignmentLeaseState fromState, String reason, Instant occurredAt) {
        DispatchAssignmentLeaseEventEntity event = new DispatchAssignmentLeaseEventEntity();
        event.leaseId = lease.leaseId();
        event.courierId = lease.courierId();
        event.orderId = lease.orderId();
        event.decisionId = lease.decisionId();
        event.generation = lease.generation();
        event.fromState = fromState;
        event.toState = lease.state();
        event.reason = reason;
        event.occurredAt = occurredAt;
        return event;
    }
}
