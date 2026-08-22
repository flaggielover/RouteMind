package com.routemind.business.domain.security;

public enum AuthorizationOutcome {
	ALLOWED,
	FORBIDDEN,
	STALE,
	REPEATED,
	INVALID_PRINCIPAL
}
