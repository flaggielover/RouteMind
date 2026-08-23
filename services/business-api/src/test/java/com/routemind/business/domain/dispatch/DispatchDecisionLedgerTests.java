package com.routemind.business.domain.dispatch;

import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class DispatchDecisionLedgerTests {

    @Test
    void onlyWallClockDispatchRecordsAreAccepted() {
        String digest = "a".repeat(64);
        String snapshot = "{\"strategy\":\"nearest\"}";
        assertThatThrownBy(() -> new DispatchDecisionLedger("decision-1", "request-1", "key-1", UUID.randomUUID(),
                UUID.randomUUID(), "nearest", "1.0.0", "dispatch-api:v1", "SIMULATED", digest, digest,
                digest, digest, snapshot, snapshot, Instant.parse("2026-08-23T00:00:00Z")))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessage("dispatch ledger clock domain must be WALL");
    }

    @Test
    void snapshotSizeAndDigestsAreBounded() {
        String digest = "a".repeat(64);
        String snapshot = "{\"strategy\":\"nearest\"}";
        assertThatThrownBy(() -> new DispatchDecisionLedger("decision-1", "request-1", "key-1", UUID.randomUUID(),
                UUID.randomUUID(), "nearest", "1.0.0", "dispatch-api:v1", "WALL", "not-a-digest", digest,
                digest, digest, snapshot, snapshot, Instant.parse("2026-08-23T00:00:00Z")))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessage("inputDigest must be a SHA-256 digest");
        assertThatThrownBy(() -> new DispatchDecisionLedger("decision-1", "request-1", "key-1", UUID.randomUUID(),
                UUID.randomUUID(), "nearest", "1.0.0", "dispatch-api:v1", "WALL", digest, digest,
                digest, digest, "x".repeat(64_001), snapshot, Instant.parse("2026-08-23T00:00:00Z")))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessage("inputSnapshotJson is invalid");
    }
}
