package com.routemind.business.api.dispatch;

import com.routemind.business.application.dispatch.DispatchDecisionLedgerRepository;
import com.routemind.business.domain.dispatch.DispatchDecisionLedger;
import java.time.Instant;
import java.util.UUID;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Read-only access to the Java-owned durable decision provenance. */
@RestController
@RequestMapping("/api/v1/dispatch-decisions")
@CrossOrigin(origins = { "http://localhost:4173", "http://127.0.0.1:4173" })
public final class DispatchDecisionLedgerController {

    private final DispatchDecisionLedgerRepository ledgers;

    public DispatchDecisionLedgerController(DispatchDecisionLedgerRepository ledgers) {
        this.ledgers = ledgers;
    }

    @GetMapping("/{decisionId}")
    public ResponseEntity<DecisionLedgerResponse> find(@PathVariable String decisionId) {
        return ledgers.findByDecisionId(decisionId)
                .map(DecisionLedgerResponse::from)
                .map(ResponseEntity::ok)
                .orElseGet(() -> ResponseEntity.notFound().build());
    }

    public record DecisionLedgerResponse(String decisionId, String requestId, String idempotencyKey,
            UUID orderId, UUID courierId, String strategy, String strategyVersion, String referenceDataId,
            String clockDomain, String inputDigest, String outputDigest, String inputSnapshotDigest,
            String outputSnapshotDigest, String inputSnapshotJson, String outputSnapshotJson, Instant createdAt) {

        static DecisionLedgerResponse from(DispatchDecisionLedger ledger) {
            return new DecisionLedgerResponse(ledger.decisionId(), ledger.requestId(), ledger.idempotencyKey(),
                    ledger.orderId(), ledger.courierId(), ledger.strategy(), ledger.strategyVersion(),
                    ledger.referenceDataId(), ledger.clockDomain(), ledger.inputDigest(), ledger.outputDigest(),
                    ledger.inputSnapshotDigest(), ledger.outputSnapshotDigest(), ledger.inputSnapshotJson(),
                    ledger.outputSnapshotJson(), ledger.createdAt());
        }
    }
}
