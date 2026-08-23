package com.routemind.business.application.reconciliation;

import java.util.List;
import java.util.Map;

public record ReconciliationCheck(String name, Status status, long inspectedCount,
		List<ReconciliationViolation> violations, Map<String, String> evidence) {

	public enum Status {
		PASS,
		FAIL,
		UNAVAILABLE
	}

	public ReconciliationCheck {
		if (name == null || name.isBlank()) throw new IllegalArgumentException("check name is required");
		if (status == null) throw new IllegalArgumentException("check status is required");
		if (inspectedCount < 0) throw new IllegalArgumentException("inspectedCount must not be negative");
		violations = List.copyOf(violations);
		evidence = Map.copyOf(evidence);
		if (status == Status.PASS && !violations.isEmpty()) {
			throw new IllegalArgumentException("a passing check cannot contain violations");
		}
		if (status == Status.FAIL && violations.isEmpty()) {
			throw new IllegalArgumentException("a failing check requires violations");
		}
	}
}
