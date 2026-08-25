package com.routemind.business.infrastructure.security;

import java.util.Collection;
import java.util.regex.Pattern;
import org.springframework.security.oauth2.core.OAuth2Error;
import org.springframework.security.oauth2.core.OAuth2TokenValidator;
import org.springframework.security.oauth2.core.OAuth2TokenValidatorResult;
import org.springframework.security.oauth2.jwt.Jwt;

public final class OidcRequiredClaimsValidator implements OAuth2TokenValidator<Jwt> {

	private static final OAuth2Error ERROR = new OAuth2Error("invalid_token", "Required identity claims are absent", null);
	private static final Pattern CLAIM_VALUE = Pattern.compile("[A-Za-z0-9][A-Za-z0-9._:-]{0,63}");
	private final String rolesClaim;

	public OidcRequiredClaimsValidator(String rolesClaim) {
		this.rolesClaim = rolesClaim;
	}

	@Override
	public OAuth2TokenValidatorResult validate(Jwt token) {
		boolean valid = safe(token.getSubject())
				&& safe(token.getId())
				&& token.getIssuedAt() != null
				&& token.getExpiresAt() != null
				&& validClaimValues(token.getClaims().get(rolesClaim))
				&& validClaimValues(token.getClaims().get("scope"));
		return valid ? OAuth2TokenValidatorResult.success() : OAuth2TokenValidatorResult.failure(ERROR);
	}

	private static boolean validClaimValues(Object claim) {
		if (claim instanceof String value) {
			var values = java.util.Arrays.stream(value.split(" ")).filter(item -> !item.isBlank()).toList();
			return !values.isEmpty() && values.stream().allMatch(OidcRequiredClaimsValidator::safe);
		}
		if (claim instanceof Collection<?> values) {
			return !values.isEmpty() && values.stream().allMatch(value -> value instanceof String text && safe(text));
		}
		return false;
	}

	private static boolean safe(String value) {
		return value != null && CLAIM_VALUE.matcher(value).matches();
	}
}
