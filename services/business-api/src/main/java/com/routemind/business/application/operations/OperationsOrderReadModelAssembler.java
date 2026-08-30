package com.routemind.business.application.operations;

import com.routemind.business.domain.dispatch.DispatchDecisionLedger;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;

/** Assembles the order context without creating a second source of truth. */
public final class OperationsOrderReadModelAssembler {

    private static final Duration DEFAULT_STALE_AFTER = Duration.ofMinutes(2);
    private final Clock clock;
    private final Duration staleAfter;

    public OperationsOrderReadModelAssembler(Clock clock) {
        this(clock, DEFAULT_STALE_AFTER);
    }

    OperationsOrderReadModelAssembler(Clock clock, Duration staleAfter) {
        this.clock = Objects.requireNonNull(clock, "clock");
        this.staleAfter = Objects.requireNonNull(staleAfter, "staleAfter");
        if (staleAfter.isNegative() || staleAfter.isZero()) {
            throw new IllegalArgumentException("staleAfter must be positive");
        }
    }

    public OperationsOrderReadModel assemble(UUID orderId, String orderStatus, Instant orderUpdatedAt,
            Optional<DispatchDecisionLedger> ledger,
            Optional<OperationsSnapshot.CourierLocationSummary> courierLocation) {
        return assemble(orderId, orderStatus, orderUpdatedAt, ledger, courierLocation, Optional.empty());
    }

    public OperationsOrderReadModel assemble(UUID orderId, String orderStatus, Instant orderUpdatedAt,
            Optional<DispatchDecisionLedger> ledger,
            Optional<OperationsSnapshot.CourierLocationSummary> courierLocation,
            Optional<OperationsOrderReadModel.RouteTravel> routeObservation) {
        Objects.requireNonNull(orderId, "orderId");
        Objects.requireNonNull(orderStatus, "orderStatus");
        Objects.requireNonNull(orderUpdatedAt, "orderUpdatedAt");
        Objects.requireNonNull(ledger, "ledger");
        Objects.requireNonNull(courierLocation, "courierLocation");
        Objects.requireNonNull(routeObservation, "routeObservation");
        Instant evaluatedAt = Instant.now(clock);
        var scopedLedger = ledger.filter(item -> item.orderId().equals(orderId));
        var decision = scopedLedger.map(this::decision).orElseGet(OperationsOrderReadModel.Decision::unavailable);
        var courier = courierLocation
                .filter(location -> scopedLedger.map(item -> item.courierId().equals(location.courierId())).orElse(false))
                .map(location -> courier(location, evaluatedAt))
                .orElseGet(OperationsOrderReadModel.Courier::unavailable);
        var route = routeObservation.map(value -> new OperationsOrderReadModel.RouteTravel(value.status(),
                value.provider(), value.fallbackUsed(), value.fallbackReason(), value.travelSeconds(),
                value.distanceKilometres(), value.observedAt(), freshness(value.observedAt(), evaluatedAt)))
                .orElseGet(OperationsOrderReadModel.RouteTravel::unavailable);
        return new OperationsOrderReadModel(decision, route, courier,
                OperationsOrderReadModel.Parties.unavailable(), freshness(orderUpdatedAt, evaluatedAt));
    }

    private OperationsOrderReadModel.Decision decision(DispatchDecisionLedger ledger) {
        var observation = ledger.observation();
        return new OperationsOrderReadModel.Decision("RECORDED", ledger.decisionId(), ledger.requestId(),
                ledger.courierId(), ledger.strategy(), ledger.strategyVersion(), ledger.referenceDataId(),
                ledger.createdAt(), observation.fallbackState(), observation.decisionReason(),
                observation.policySelectionMode(), observation.decisionProvenanceReference());
    }

    private OperationsOrderReadModel.Courier courier(OperationsSnapshot.CourierLocationSummary location,
            Instant evaluatedAt) {
        var freshness = freshness(location.ingestedAt(), evaluatedAt);
        String status = freshness.status();
        return new OperationsOrderReadModel.Courier(status, location.courierId(),
                location.online() ? "ONLINE" : "OFFLINE", location.sequence(), location.observedAt(),
                location.ingestedAt(), freshness);
    }

    private OperationsOrderReadModel.Freshness freshness(Instant observedAt, Instant evaluatedAt) {
        if (observedAt == null) return OperationsOrderReadModel.Freshness.unavailable(null, evaluatedAt);
        return Duration.between(observedAt, evaluatedAt).compareTo(staleAfter) > 0
                ? OperationsOrderReadModel.Freshness.stale(observedAt, evaluatedAt)
                : OperationsOrderReadModel.Freshness.current(observedAt, evaluatedAt);
    }
}
