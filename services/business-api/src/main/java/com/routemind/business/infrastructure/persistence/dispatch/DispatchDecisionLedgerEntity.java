package com.routemind.business.infrastructure.persistence.dispatch;

import com.routemind.business.domain.dispatch.DispatchDecisionLedger;
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
@Table(name = "dispatch_decision_ledger", schema = "routemind")
class DispatchDecisionLedgerEntity extends TenantScopedEntity {

    @Id @Column(name = "decision_id", length = 128) private String decisionId;
    @Column(name = "logical_decision_id", nullable = false, length = 128) private String logicalDecisionId;
    @Column(name = "request_id", nullable = false, length = 128) private String requestId;
    @Column(name = "idempotency_key", nullable = false, length = 128) private String idempotencyKey;
    @Column(name = "logical_idempotency_key", nullable = false, length = 128) private String logicalIdempotencyKey;
    @Column(name = "order_id", nullable = false) private UUID orderId;
    @Column(name = "courier_id", nullable = false) private UUID courierId;
    @Column(nullable = false, length = 64) private String strategy;
    @Column(name = "strategy_version", nullable = false, length = 64) private String strategyVersion;
    @Column(name = "reference_data_id", nullable = false, length = 256) private String referenceDataId;
    @Column(name = "clock_domain", nullable = false, length = 16) private String clockDomain;
    @Column(name = "input_digest", nullable = false, length = 64) private String inputDigest;
    @Column(name = "output_digest", nullable = false, length = 64) private String outputDigest;
    @Column(name = "input_snapshot_digest", nullable = false, length = 64) private String inputSnapshotDigest;
    @Column(name = "output_snapshot_digest", nullable = false, length = 64) private String outputSnapshotDigest;
    @Column(name = "input_snapshot_json", nullable = false, columnDefinition = "TEXT") private String inputSnapshotJson;
    @Column(name = "output_snapshot_json", nullable = false, columnDefinition = "TEXT") private String outputSnapshotJson;
    @Column(name = "created_at", nullable = false) private Instant createdAt;

    protected DispatchDecisionLedgerEntity() {
    }

    static DispatchDecisionLedgerEntity from(DispatchDecisionLedger ledger, UUID tenantId) {
        DispatchDecisionLedgerEntity entity = new DispatchDecisionLedgerEntity();
        entity.assignTenant(tenantId);
        entity.decisionId = TenantKey.encode(tenantId, ledger.decisionId());
        entity.logicalDecisionId = ledger.decisionId();
        entity.idempotencyKey = TenantKey.encode(tenantId, ledger.idempotencyKey());
        entity.logicalIdempotencyKey = ledger.idempotencyKey();
        entity.apply(ledger);
        return entity;
    }

    void apply(DispatchDecisionLedger ledger) {
        if (logicalDecisionId != null && !logicalDecisionId.equals(ledger.decisionId())) throw new TenantIsolationException();
        if (logicalIdempotencyKey != null && !logicalIdempotencyKey.equals(ledger.idempotencyKey())) throw new TenantIsolationException();
        logicalDecisionId = ledger.decisionId();
        logicalIdempotencyKey = ledger.idempotencyKey();
        requestId = ledger.requestId();
        orderId = ledger.orderId();
        courierId = ledger.courierId();
        strategy = ledger.strategy();
        strategyVersion = ledger.strategyVersion();
        referenceDataId = ledger.referenceDataId();
        clockDomain = ledger.clockDomain();
        inputDigest = ledger.inputDigest();
        outputDigest = ledger.outputDigest();
        inputSnapshotDigest = ledger.inputSnapshotDigest();
        outputSnapshotDigest = ledger.outputSnapshotDigest();
        inputSnapshotJson = ledger.inputSnapshotJson();
        outputSnapshotJson = ledger.outputSnapshotJson();
        createdAt = ledger.createdAt();
    }

    DispatchDecisionLedger toDomain() {
        return new DispatchDecisionLedger(logicalDecisionId, requestId, logicalIdempotencyKey, orderId, courierId, strategy,
                strategyVersion, referenceDataId, clockDomain, inputDigest, outputDigest, inputSnapshotDigest,
                outputSnapshotDigest, inputSnapshotJson, outputSnapshotJson, createdAt);
    }
}
