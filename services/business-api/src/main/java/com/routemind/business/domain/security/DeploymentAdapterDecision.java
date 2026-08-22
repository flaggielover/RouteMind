package com.routemind.business.domain.security;

public record DeploymentAdapterDecision(
		AdapterOutcome outcome,
		String reason,
		String operationId,
		String provider,
		String providerVersion,
		boolean localReadOnly) {

	public DeploymentAdapterDecision {
		if (outcome == null || reason == null || reason.isBlank() || operationId == null || operationId.isBlank()
				|| provider == null || provider.isBlank() || providerVersion == null || providerVersion.isBlank()) {
			throw new IllegalArgumentException("deployment decision fields are required");
		}
	}
}
