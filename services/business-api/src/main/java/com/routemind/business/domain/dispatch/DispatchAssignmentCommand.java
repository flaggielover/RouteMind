package com.routemind.business.domain.dispatch;

import java.util.Objects;
import java.util.UUID;
import java.util.regex.Pattern;

public record DispatchAssignmentCommand(String requestId, String contractVersion, UUID courierId,
        String strategy, String strategyVersion, String inputDigest, String outputDigest,
        boolean fallbackUsed, String fallbackReason, long expectedOrderVersion) {

    private static final Pattern DIGEST = Pattern.compile("[0-9a-f]{64}");

    public DispatchAssignmentCommand {
        requireText(requestId, "requestId", 128);
        if (!"v1".equals(contractVersion)) throw new IllegalArgumentException("unsupported_contract_version");
        Objects.requireNonNull(courierId, "courierId");
        requireText(strategy, "strategy", 64);
        requireText(strategyVersion, "strategyVersion", 64);
        requireDigest(inputDigest, "inputDigest");
        requireDigest(outputDigest, "outputDigest");
        if (fallbackUsed) requireText(fallbackReason, "fallbackReason", 256);
        if (expectedOrderVersion < 0) throw new IllegalArgumentException("expectedOrderVersion must not be negative");
    }

    private static void requireDigest(String value, String name) {
        if (value == null || !DIGEST.matcher(value).matches()) throw new IllegalArgumentException(name + " must be a SHA-256 digest");
    }

    private static void requireText(String value, String name, int maxLength) {
        if (value == null || value.isBlank() || value.length() > maxLength
                || value.chars().anyMatch(Character::isISOControl)) {
            throw new IllegalArgumentException(name + " is invalid");
        }
    }
}
