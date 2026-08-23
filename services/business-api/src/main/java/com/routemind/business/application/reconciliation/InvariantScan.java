package com.routemind.business.application.reconciliation;

import java.util.List;
import java.util.Map;

public record InvariantScan(long inspectedCount, List<ReconciliationViolation> violations,
		Map<String, String> evidence) {

	public InvariantScan {
		if (inspectedCount < 0) throw new IllegalArgumentException("inspectedCount must not be negative");
		violations = List.copyOf(violations);
		evidence = Map.copyOf(evidence);
	}
}
