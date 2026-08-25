package com.routemind.business.application.security;

public final class TenantIsolationException extends RuntimeException {

	public TenantIsolationException() {
		super("tenant_scope_violation");
	}
}
