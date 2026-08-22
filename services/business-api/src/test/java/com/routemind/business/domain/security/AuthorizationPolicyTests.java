package com.routemind.business.domain.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Instant;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

class AuthorizationPolicyTests {

	private static final Instant NOW = Instant.parse("2026-08-22T07:00:00Z");
	private static final AuthenticatedPrincipal OPERATOR = new AuthenticatedPrincipal("subject-1", "issuer-1",
			"token-1", NOW.minusSeconds(60), NOW.minusSeconds(60), NOW.plusSeconds(600), "routemind",
			Set.of("operator"), Set.of("order:write"), true);
	private static final AuthorizationPolicy POLICY = new AuthorizationPolicy("issuer-1", "routemind", "policy-v1",
			List.of(new AuthorizationRule("operator", "order.update", "order", "order:write")));

	@Test
	void allowsActivePrincipalWithRoleScopeAndCurrentVersion() {
		AuthorizationDecision decision = POLICY.evaluate(OPERATOR,
				new CommandAuthorizationRequest("order.update", "order", 3, 3, false), NOW);

		assertThat(decision).isEqualTo(new AuthorizationDecision(AuthorizationOutcome.ALLOWED, "authorized", "policy-v1"));
	}

	@Test
	void deniesByDefaultWhenRoleOrScopeDoesNotMatch() {
		AuthenticatedPrincipal courier = new AuthenticatedPrincipal("subject-2", "issuer-1", "token-2",
				NOW.minusSeconds(60), NOW.minusSeconds(60), NOW.plusSeconds(600), "routemind", Set.of("courier"),
				Set.of("order:read"), true);

		AuthorizationDecision decision = POLICY.evaluate(courier,
				new CommandAuthorizationRequest("order.update", "order", 3, 3, false), NOW);

		assertThat(decision.outcome()).isEqualTo(AuthorizationOutcome.FORBIDDEN);
		assertThat(decision.reason()).isEqualTo("permission_denied");
	}

	@Test
	void rejectsExpiredAndUnknownIssuerPrincipalsWithoutLoggingCredentialContents() {
		AuthenticatedPrincipal expired = new AuthenticatedPrincipal("subject-3", "issuer-1", "token-3",
				NOW.minusSeconds(600), NOW.minusSeconds(600), NOW, "routemind", Set.of("operator"),
				Set.of("order:write"), true);
		AuthenticatedPrincipal unknownIssuer = new AuthenticatedPrincipal("subject-4", "untrusted", "token-4",
				NOW.minusSeconds(60), NOW.minusSeconds(60), NOW.plusSeconds(600), "routemind", Set.of("operator"),
				Set.of("order:write"), true);
		CommandAuthorizationRequest request = new CommandAuthorizationRequest("order.update", "order", 3, 3, false);

		assertThat(POLICY.evaluate(expired, request, NOW).reason()).isEqualTo("credential_expired");
		assertThat(POLICY.evaluate(unknownIssuer, request, NOW).reason()).isEqualTo("unknown_issuer");
	}

	@Test
	void distinguishesRepeatedAndStaleCommandsBeforePermissionEvaluation() {
		CommandAuthorizationRequest repeated = new CommandAuthorizationRequest("order.update", "order", 2, 3, true);
		CommandAuthorizationRequest stale = new CommandAuthorizationRequest("order.update", "order", 2, 3, false);

		assertThat(POLICY.evaluate(OPERATOR, repeated, NOW).outcome()).isEqualTo(AuthorizationOutcome.REPEATED);
		assertThat(POLICY.evaluate(OPERATOR, stale, NOW).outcome()).isEqualTo(AuthorizationOutcome.STALE);
	}

	@Test
	void rejectsMalformedPrincipalAndCommandAtTheBoundary() {
		assertThatThrownBy(() -> new AuthenticatedPrincipal(" ", "issuer", "token", NOW, NOW, NOW.plusSeconds(1),
				"audience", Set.of("operator"), Set.of("order:write"), true))
				.isInstanceOf(IllegalArgumentException.class)
				.hasMessageContaining("subject");
		assertThatThrownBy(() -> new CommandAuthorizationRequest("order.update", "order", -1, 0, false))
				.isInstanceOf(IllegalArgumentException.class)
				.hasMessageContaining("non-negative");
	}
}
