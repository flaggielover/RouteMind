package com.routemind.business.infrastructure.security;

import static org.assertj.core.api.Assertions.assertThat;

import com.routemind.business.domain.security.AuthenticatedPrincipal;
import java.net.URI;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.security.oauth2.jwt.Jwt;

class OidcTokenBoundaryTests {

	private static final Instant NOW = Instant.parse("2026-08-25T08:00:00Z");
	private static final OidcSecurityProperties PROPERTIES = new OidcSecurityProperties(true,
			URI.create("https://identity.example/issuer"), "routemind-business-api",
			URI.create("https://identity.example/jwks"), "roles", false);

	@Test
	void rejectsWrongAudienceAndReplayUnsafeIdentity() {
		Jwt wrongAudience = token(List.of("other-api"), "token-1", List.of("operator"), "order:write");
		Jwt missingTokenId = token(List.of("routemind-business-api"), null, List.of("operator"), "order:write");
		Jwt malformedScope = token(List.of("routemind-business-api"), "token-2", List.of("operator"),
				"order:write injected/authority");
		Jwt malformedRole = token(List.of("routemind-business-api"), "token-3",
				List.of("operator", "injected role"), "order:write");

		assertThat(new OidcAudienceValidator(PROPERTIES.audience()).validate(wrongAudience).hasErrors()).isTrue();
		assertThat(new OidcRequiredClaimsValidator("roles").validate(missingTokenId).hasErrors()).isTrue();
		assertThat(new OidcRequiredClaimsValidator("roles").validate(malformedScope).hasErrors()).isTrue();
		assertThat(new OidcRequiredClaimsValidator("roles").validate(malformedRole).hasErrors()).isTrue();
	}

	@Test
	void mapsValidatedIdentityToFrameworkAndDurablePolicyRepresentations() {
		Jwt token = token(List.of("routemind-business-api", "other-api"), "token-2",
				List.of("operator", "analyst"), "order:write report:read");

		assertThat(new OidcAudienceValidator(PROPERTIES.audience()).validate(token).hasErrors()).isFalse();
		assertThat(new OidcRequiredClaimsValidator("roles").validate(token).hasErrors()).isFalse();
		assertThat(new OidcAuthorityConverter("roles").convert(token))
				.extracting(Object::toString)
				.containsExactlyInAnyOrder("ROLE_OPERATOR", "ROLE_ANALYST", "SCOPE_order:write", "SCOPE_report:read");

		AuthenticatedPrincipal principal = new OidcPrincipalMapper(PROPERTIES).map(token);
		assertThat(principal.subject()).isEqualTo("subject-1");
		assertThat(principal.tokenId()).isEqualTo("token-2");
		assertThat(principal.roles()).containsExactlyInAnyOrder("operator", "analyst");
		assertThat(principal.scopes()).containsExactlyInAnyOrder("order:write", "report:read");
	}

	private static Jwt token(List<String> audience, String tokenId, List<String> roles, String scope) {
		return Jwt.withTokenValue("redacted")
				.header("alg", "RS256")
				.subject("subject-1")
				.issuer(PROPERTIES.issuer().toString())
				.audience(audience)
				.claim("jti", tokenId)
				.claim("roles", roles)
				.claim("scope", scope)
				.issuedAt(NOW.minusSeconds(30))
				.notBefore(NOW.minusSeconds(30))
				.expiresAt(NOW.plusSeconds(300))
				.build();
	}
}
