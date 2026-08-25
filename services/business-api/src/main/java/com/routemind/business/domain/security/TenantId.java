package com.routemind.business.domain.security;

import java.util.Objects;
import java.util.UUID;

public record TenantId(UUID value) {

	public static final TenantId LEGACY = new TenantId(UUID.fromString("00000000-0000-0000-0000-000000000001"));

	public TenantId {
		Objects.requireNonNull(value, "tenantId");
		if (value.equals(new UUID(0, 0))) {
			throw new IllegalArgumentException("tenantId must not be the nil UUID");
		}
	}

	public static TenantId parse(String value) {
		try {
			String canonical = Objects.requireNonNull(value, "tenantId").trim();
			UUID parsed = UUID.fromString(canonical);
			if (!parsed.toString().equals(canonical)) {
				throw new IllegalArgumentException("tenantId is not canonical");
			}
			return new TenantId(parsed);
		}
		catch (IllegalArgumentException exception) {
			throw new IllegalArgumentException("tenantId must be a canonical non-nil UUID", exception);
		}
	}
}
