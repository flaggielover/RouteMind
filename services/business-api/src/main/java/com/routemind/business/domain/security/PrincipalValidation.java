package com.routemind.business.domain.security;

public record PrincipalValidation(boolean accepted, String reason) {

	public PrincipalValidation {
		if (reason == null || reason.isBlank()) {
			throw new IllegalArgumentException("reason must not be blank");
		}
	}
}
