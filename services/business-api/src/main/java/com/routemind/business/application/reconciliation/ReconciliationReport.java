package com.routemind.business.application.reconciliation;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record ReconciliationReport(UUID runId, Instant checkedAt, Status status, String repairMode,
		int violationCount, int unavailableCount, List<ReconciliationCheck> checks) {

	public enum Status {
		HEALTHY,
		DRIFT_DETECTED,
		DEGRADED
	}

	public ReconciliationReport {
		if (runId == null || checkedAt == null || status == null) {
			throw new IllegalArgumentException("run identity, time, and status are required");
		}
		if (!"DETECT_ONLY".equals(repairMode)) throw new IllegalArgumentException("repair mode must be DETECT_ONLY");
		if (violationCount < 0 || unavailableCount < 0) {
			throw new IllegalArgumentException("report counts must not be negative");
		}
		checks = List.copyOf(checks);
	}
}
