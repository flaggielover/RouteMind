package com.routemind.business.application.reconciliation;

import java.util.Map;

public record ReconciliationViolation(String code, String entityType, String entityId,
		Map<String, String> evidence) {

	public ReconciliationViolation {
		if (code == null || code.isBlank()) throw new IllegalArgumentException("violation code is required");
		if (entityType == null || entityType.isBlank()) throw new IllegalArgumentException("entity type is required");
		if (entityId == null || entityId.isBlank()) throw new IllegalArgumentException("entity id is required");
		evidence = Map.copyOf(evidence);
	}
}
