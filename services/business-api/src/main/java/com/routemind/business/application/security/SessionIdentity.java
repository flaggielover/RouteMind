package com.routemind.business.application.security;

import com.routemind.business.domain.security.TenantId;
import java.time.Instant;
import java.util.Set;

public record SessionIdentity(String subject, TenantId tenantId, Set<String> roles, Instant expiresAt) {

	public SessionIdentity {
		if (subject == null || subject.isBlank() || tenantId == null || expiresAt == null) {
			throw new IllegalArgumentException("session identity fields are required");
		}
		roles = roles == null ? Set.of() : Set.copyOf(roles);
		if (roles.isEmpty()) {
			throw new IllegalArgumentException("session identity roles are required");
		}
	}
}
