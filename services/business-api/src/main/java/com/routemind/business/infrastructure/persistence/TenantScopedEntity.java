package com.routemind.business.infrastructure.persistence;

import com.routemind.business.application.security.TenantIsolationException;
import jakarta.persistence.Column;
import jakarta.persistence.MappedSuperclass;
import java.util.Objects;
import java.util.UUID;

@MappedSuperclass
public abstract class TenantScopedEntity {

	@Column(name = "tenant_id", nullable = false, updatable = false)
	private UUID tenantId;

	public final UUID tenantId() {
		return tenantId;
	}

	public final void assignTenant(UUID tenantId) {
		Objects.requireNonNull(tenantId, "tenantId");
		if (this.tenantId != null && !this.tenantId.equals(tenantId)) {
			throw new TenantIsolationException();
		}
		this.tenantId = tenantId;
	}
}
