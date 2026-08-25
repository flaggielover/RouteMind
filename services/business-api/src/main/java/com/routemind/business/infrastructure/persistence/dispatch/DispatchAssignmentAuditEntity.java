package com.routemind.business.infrastructure.persistence.dispatch;

import com.routemind.business.domain.dispatch.DispatchAssignmentAudit;
import com.routemind.business.application.security.TenantIsolationException;
import com.routemind.business.infrastructure.persistence.TenantKey;
import com.routemind.business.infrastructure.persistence.TenantScopedEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "dispatch_assignment_audits", schema = "routemind")
class DispatchAssignmentAuditEntity extends TenantScopedEntity {

    @Id
    @Column(name = "idempotency_key", length = 128)
    private String idempotencyKey;

    @Column(name = "logical_key", nullable = false, length = 128)
    private String logicalKey;

    @Column(name = "request_hash", nullable = false, length = 64)
    private String requestHash;

    @Column(name = "request_id", nullable = false, length = 128)
    private String requestId;

    @Column(name = "order_id", nullable = false)
    private UUID orderId;

    @Column(name = "courier_id", nullable = false)
    private UUID courierId;

    @Column(name = "contract_version", nullable = false, length = 16)
    private String contractVersion;

    @Column(nullable = false, length = 64)
    private String strategy;

    @Column(name = "strategy_version", nullable = false, length = 64)
    private String strategyVersion;

    @Column(name = "input_digest", nullable = false, length = 64)
    private String inputDigest;

    @Column(name = "output_digest", nullable = false, length = 64)
    private String outputDigest;

    @Column(name = "trace_id", nullable = false, length = 32)
    private String traceId;

    @Column(name = "fallback_used", nullable = false)
    private boolean fallbackUsed;

    @Column(name = "fallback_reason", length = 256)
    private String fallbackReason;

    @Column(name = "applied_order_version", nullable = false)
    private long appliedOrderVersion;

    @Column(name = "lease_id")
    private UUID leaseId;

    @Column(name = "lease_generation")
    private Long leaseGeneration;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    protected DispatchAssignmentAuditEntity() {
    }

    static DispatchAssignmentAuditEntity from(DispatchAssignmentAudit audit, UUID tenantId) {
        DispatchAssignmentAuditEntity entity = new DispatchAssignmentAuditEntity();
        entity.assignTenant(tenantId);
        entity.idempotencyKey = TenantKey.encode(tenantId, audit.idempotencyKey());
        entity.logicalKey = audit.idempotencyKey();
        entity.apply(audit);
        return entity;
    }

    void apply(DispatchAssignmentAudit audit) {
        if (logicalKey != null && !logicalKey.equals(audit.idempotencyKey())) throw new TenantIsolationException();
        logicalKey = audit.idempotencyKey();
        requestHash = audit.requestHash();
        requestId = audit.requestId();
        orderId = audit.orderId();
        courierId = audit.courierId();
        contractVersion = audit.contractVersion();
        strategy = audit.strategy();
        strategyVersion = audit.strategyVersion();
        inputDigest = audit.inputDigest();
        outputDigest = audit.outputDigest();
        traceId = audit.traceId();
        fallbackUsed = audit.fallbackUsed();
        fallbackReason = audit.fallbackReason();
        appliedOrderVersion = audit.appliedOrderVersion();
        leaseId = audit.leaseId();
        leaseGeneration = audit.leaseGeneration();
        createdAt = audit.createdAt();
    }

    DispatchAssignmentAudit toDomain() {
        return new DispatchAssignmentAudit(logicalKey, requestHash, requestId, orderId, courierId,
                contractVersion, strategy, strategyVersion, inputDigest, outputDigest, traceId, fallbackUsed,
                fallbackReason, appliedOrderVersion, leaseId, leaseGeneration, createdAt);
    }
}
