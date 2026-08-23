package com.routemind.business.domain.dispatch;

import java.time.Instant;
import java.util.UUID;

public record DispatchAssignmentAudit(String idempotencyKey, String requestHash, String requestId,
        UUID orderId, UUID courierId, String contractVersion, String strategy, String strategyVersion,
        String inputDigest, String outputDigest, String traceId, boolean fallbackUsed,
        String fallbackReason, long appliedOrderVersion, UUID leaseId, Long leaseGeneration, Instant createdAt) {
}
