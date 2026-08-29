package com.routemind.business.domain.dispatch;

import java.util.regex.Pattern;

/** Optional provenance supplied by a compute or simulation caller. */
public record DispatchObservationMetadata(String schemaVersion, String runId, String scenarioId,
        Long simulationTick, String decisionReason, String policySelectionMode, String fallbackState,
        String configurationDigest, Long deterministicSeed, String stateSnapshotReference,
        String decisionProvenanceReference) {

    private static final Pattern DIGEST = Pattern.compile("[0-9a-f]{64}");

    public DispatchObservationMetadata {
        if (!"routemind-policy-observation-v1".equals(schemaVersion)) {
            throw new IllegalArgumentException("unsupported observation schema version");
        }
        requireOptionalText(runId, "runId", 256);
        requireOptionalText(scenarioId, "scenarioId", 256);
        requireText(decisionReason, "decisionReason", 128);
        requireText(policySelectionMode, "policySelectionMode", 128);
        requireText(fallbackState, "fallbackState", 64);
        if (simulationTick != null && simulationTick < 0) throw new IllegalArgumentException("simulationTick must be non-negative");
        if (deterministicSeed != null && deterministicSeed < 0) throw new IllegalArgumentException("deterministicSeed must be non-negative");
        if (configurationDigest != null && !DIGEST.matcher(configurationDigest).matches()) {
            throw new IllegalArgumentException("configurationDigest must be a SHA-256 digest");
        }
        requireOptionalText(stateSnapshotReference, "stateSnapshotReference", 256);
        requireOptionalText(decisionProvenanceReference, "decisionProvenanceReference", 256);
    }

    public static DispatchObservationMetadata empty() {
        return new DispatchObservationMetadata("routemind-policy-observation-v1", null, null, null,
                "dispatch_assignment", "java_command", "NONE", null, null, null, null);
    }

    public DispatchObservationMetadata effectiveFallback(boolean fallbackUsed) {
        if (!fallbackUsed || !"NONE".equals(fallbackState)) return this;
        return new DispatchObservationMetadata(schemaVersion, runId, scenarioId, simulationTick,
                decisionReason, policySelectionMode, "FALLBACK_USED", configurationDigest,
                deterministicSeed, stateSnapshotReference, decisionProvenanceReference);
    }

    private static void requireOptionalText(String value, String name, int maxLength) {
        if (value != null) requireText(value, name, maxLength);
    }

    private static void requireText(String value, String name, int maxLength) {
        if (value == null || value.isBlank() || value.length() > maxLength
                || value.chars().anyMatch(Character::isISOControl)) {
            throw new IllegalArgumentException(name + " is invalid");
        }
    }
}
