package com.routemind.business.domain.dispatch;

import java.time.Instant;
import java.util.Objects;
import java.util.UUID;
import java.util.regex.Pattern;

public record DispatchDecisionLedger(String decisionId, String requestId, String idempotencyKey,
        UUID orderId, UUID courierId, String strategy, String strategyVersion, String referenceDataId,
        String clockDomain, String inputDigest, String outputDigest, String inputSnapshotDigest,
        String outputSnapshotDigest, String inputSnapshotJson, String outputSnapshotJson, Instant createdAt) {

    private static final Pattern DIGEST = Pattern.compile("[0-9a-f]{64}");

    public DispatchDecisionLedger {
        requireText(decisionId, "decisionId", 128);
        requireText(requestId, "requestId", 128);
        requireText(idempotencyKey, "idempotencyKey", 128);
        Objects.requireNonNull(orderId, "orderId");
        Objects.requireNonNull(courierId, "courierId");
        requireText(strategy, "strategy", 64);
        requireText(strategyVersion, "strategyVersion", 64);
        requireText(referenceDataId, "referenceDataId", 256);
        if (!"WALL".equals(clockDomain)) throw new IllegalArgumentException("dispatch ledger clock domain must be WALL");
        requireDigest(inputDigest, "inputDigest");
        requireDigest(outputDigest, "outputDigest");
        requireDigest(inputSnapshotDigest, "inputSnapshotDigest");
        requireDigest(outputSnapshotDigest, "outputSnapshotDigest");
        requireSnapshot(inputSnapshotJson, "inputSnapshotJson");
        requireSnapshot(outputSnapshotJson, "outputSnapshotJson");
        Objects.requireNonNull(createdAt, "createdAt");
    }

    private static void requireDigest(String value, String name) {
        if (value == null || !DIGEST.matcher(value).matches()) throw new IllegalArgumentException(name + " must be a SHA-256 digest");
    }

    private static void requireSnapshot(String value, String name) {
        if (value == null || value.isBlank() || value.length() > 64_000) throw new IllegalArgumentException(name + " is invalid");
    }

    private static void requireText(String value, String name, int maxLength) {
        if (value == null || value.isBlank() || value.length() > maxLength || value.chars().anyMatch(Character::isISOControl)) {
            throw new IllegalArgumentException(name + " is invalid");
        }
    }
}
