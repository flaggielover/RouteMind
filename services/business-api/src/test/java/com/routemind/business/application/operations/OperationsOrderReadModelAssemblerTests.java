package com.routemind.business.application.operations;

import static org.assertj.core.api.Assertions.assertThat;

import com.routemind.business.domain.dispatch.DispatchDecisionLedger;
import com.routemind.business.domain.dispatch.DispatchObservationMetadata;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class OperationsOrderReadModelAssemblerTests {

    private static final Instant NOW = Instant.parse("2026-08-30T08:00:00Z");
    private static final UUID ORDER_ID = UUID.fromString("10000000-0000-4000-8000-000000000001");
    private static final UUID COURIER_ID = UUID.fromString("20000000-0000-4000-8000-000000000001");
    private static final String DIGEST = "a".repeat(64);

    private final OperationsOrderReadModelAssembler assembler = new OperationsOrderReadModelAssembler(
            Clock.fixed(NOW, ZoneOffset.UTC));

    @Test
    void completeDecisionLedgerAndCourierStateRemainOrderScoped() {
        var ledger = ledger(ORDER_ID, COURIER_ID, "risk-aware", "FALLBACK_USED");
        var location = location(COURIER_ID, NOW.minusSeconds(30));

        var result = assembler.assemble(ORDER_ID, "ASSIGNED", NOW.minusSeconds(20), Optional.of(ledger),
                Optional.of(location));

        assertThat(result.decision().status()).isEqualTo("RECORDED");
        assertThat(result.decision().decisionId()).isEqualTo("decision-1");
        assertThat(result.decision().strategy()).isEqualTo("risk-aware");
        assertThat(result.decision().fallbackState()).isEqualTo("FALLBACK_USED");
        assertThat(result.courier().courierId()).isEqualTo(COURIER_ID);
        assertThat(result.courier().status()).isEqualTo("CURRENT");
        assertThat(result.route().status()).isEqualTo("NO_ROUTE_ESTIMATE");
        assertThat(result.orderFreshness().status()).isEqualTo("CURRENT");
    }

    @Test
    void orderBeforeDispatchIsExplicitlyUnavailable() {
        var result = assembler.assemble(ORDER_ID, "CONFIRMED", NOW.minusSeconds(10), Optional.empty(),
                Optional.of(location(COURIER_ID, NOW.minusSeconds(10))));

        assertThat(result.decision().status()).isEqualTo("NO_DECISION_YET");
        assertThat(result.courier().status()).isEqualTo("UNAVAILABLE");
        assertThat(result.parties().linkageStatus()).isEqualTo("UNAVAILABLE");
    }

    @Test
    void fallbackRouteAndStaleRouteAreRepresentedWithoutInference() {
        var route = new OperationsOrderReadModel.RouteTravel("DEGRADED", "local-fallback", true,
                "primary_timeout", 120.0, 1.2, NOW.minusSeconds(180), null);
        var result = assembler.assemble(ORDER_ID, "ASSIGNED", NOW.minusSeconds(180),
                Optional.of(ledger(ORDER_ID, COURIER_ID, "nearest", "NONE")),
                Optional.of(location(COURIER_ID, NOW.minusSeconds(180))), Optional.of(route));

        assertThat(result.route().status()).isEqualTo("DEGRADED");
        assertThat(result.route().fallbackUsed()).isTrue();
        assertThat(result.route().freshness().status()).isEqualTo("STALE");
        assertThat(result.courier().freshness().status()).isEqualTo("STALE");
    }

    @Test
    void missingLedgerCannotLeakAnotherOrdersCourier() {
        var otherOrder = UUID.fromString("10000000-0000-4000-8000-000000000002");
        var result = assembler.assemble(ORDER_ID, "ASSIGNED", NOW, Optional.of(ledger(otherOrder, COURIER_ID,
                "nearest", "NONE")), Optional.of(location(COURIER_ID, NOW)));

        assertThat(result.decision().status()).isEqualTo("NO_DECISION_YET");
        assertThat(result.courier().status()).isEqualTo("UNAVAILABLE");
    }

    @Test
    void terminalOrderAndTimestampEvaluationAreDeterministic() {
        var first = assembler.assemble(ORDER_ID, "DELIVERED", NOW.minusSeconds(1), Optional.empty(), Optional.empty());
        var second = assembler.assemble(ORDER_ID, "DELIVERED", NOW.minusSeconds(1), Optional.empty(), Optional.empty());

        assertThat(first).isEqualTo(second);
        assertThat(first.orderFreshness().evaluatedAt()).isEqualTo(NOW);
        assertThat(first.route().status()).isEqualTo("NO_ROUTE_ESTIMATE");
    }

    private static DispatchDecisionLedger ledger(UUID orderId, UUID courierId, String strategy,
            String fallbackState) {
        return new DispatchDecisionLedger("decision-1", "request-1", "idempotency-1", orderId, courierId,
                strategy, "1.0.0", "dispatch-api:v1", "WALL", DIGEST, DIGEST, DIGEST, DIGEST,
                "{\"strategy\":\"" + strategy + "\"}", "{\"status\":\"ASSIGNED\"}", NOW.minusSeconds(30),
                new DispatchObservationMetadata("routemind-policy-observation-v1", "run-1", "scenario-1", 1L,
                        "dispatch_assignment", "python_compute", fallbackState, DIGEST, 7L, "state-1", "prov-1"));
    }

    private static OperationsSnapshot.CourierLocationSummary location(UUID courierId, Instant observedAt) {
        return new OperationsSnapshot.CourierLocationSummary(courierId, 31.2, 121.4, 4, observedAt,
                observedAt.plusSeconds(1), true);
    }
}
