package com.routemind.business.application.operations;

import java.time.Instant;
import java.util.UUID;

/**
 * One order-centric, read-only view assembled from authoritative business sources.
 * Optional relationships are represented by a status instead of a presentation guess.
 */
public record OperationsOrderReadModel(Decision decision, RouteTravel route, Courier courier,
        Parties parties, Freshness orderFreshness) {

    public OperationsOrderReadModel {
        if (decision == null || route == null || courier == null || parties == null || orderFreshness == null) {
            throw new IllegalArgumentException("operational order context is incomplete");
        }
    }

    public static OperationsOrderReadModel unavailable() {
        var freshness = Freshness.unavailable(null, null);
        return new OperationsOrderReadModel(Decision.unavailable(), RouteTravel.unavailable(),
                Courier.unavailable(), Parties.unavailable(), freshness);
    }

    public record Decision(String status, String decisionId, String requestId, UUID courierId,
            String strategy, String strategyVersion, String referenceDataId, Instant decidedAt,
            String fallbackState, String decisionReason, String policySelectionMode,
            String provenanceReference) {

        static Decision unavailable() {
            return new Decision("NO_DECISION_YET", null, null, null, null, null, null, null,
                    "NONE", null, null, null);
        }
    }

    public record RouteTravel(String status, String provider, Boolean fallbackUsed,
            String fallbackReason, Double travelSeconds, Double distanceKilometres,
            Instant observedAt, Freshness freshness) {

        static RouteTravel unavailable() {
            return new RouteTravel("NO_ROUTE_ESTIMATE", null, null, null, null, null, null,
                    Freshness.unavailable(null, null));
        }
    }

    public record Courier(String status, UUID courierId, String lifecycleStatus, long sequence,
            Instant observedAt, Instant ingestedAt, Freshness freshness) {

        static Courier unavailable() {
            return new Courier("UNAVAILABLE", null, null, 0, null, null,
                    Freshness.unavailable(null, null));
        }
    }

    public record Parties(String linkageStatus, String customerStatus, String merchantStatus) {

        static Parties unavailable() {
            return new Parties("UNAVAILABLE", null, null);
        }
    }

    public record Freshness(String status, Instant observedAt, Instant evaluatedAt) {

        static Freshness unavailable(Instant observedAt, Instant evaluatedAt) {
            return new Freshness("UNAVAILABLE", observedAt, evaluatedAt);
        }

        static Freshness current(Instant observedAt, Instant evaluatedAt) {
            return new Freshness("CURRENT", observedAt, evaluatedAt);
        }

        static Freshness stale(Instant observedAt, Instant evaluatedAt) {
            return new Freshness("STALE", observedAt, evaluatedAt);
        }
    }
}
