package com.routemind.business.infrastructure.security;

import org.springframework.security.oauth2.core.OAuth2Error;
import org.springframework.security.oauth2.core.OAuth2TokenValidator;
import org.springframework.security.oauth2.core.OAuth2TokenValidatorResult;
import org.springframework.security.oauth2.jwt.Jwt;

public final class OidcAudienceValidator implements OAuth2TokenValidator<Jwt> {

	private static final OAuth2Error ERROR = new OAuth2Error("invalid_token", "Required audience is absent", null);
	private final String requiredAudience;

	public OidcAudienceValidator(String requiredAudience) {
		if (requiredAudience == null || requiredAudience.isBlank()) {
			throw new IllegalArgumentException("requiredAudience must not be blank");
		}
		this.requiredAudience = requiredAudience.trim();
	}

	@Override
	public OAuth2TokenValidatorResult validate(Jwt token) {
		return token.getAudience().contains(requiredAudience)
				? OAuth2TokenValidatorResult.success()
				: OAuth2TokenValidatorResult.failure(ERROR);
	}
}
