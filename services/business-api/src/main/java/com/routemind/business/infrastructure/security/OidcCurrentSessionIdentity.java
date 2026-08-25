package com.routemind.business.infrastructure.security;

import com.routemind.business.application.security.CurrentSessionIdentity;
import com.routemind.business.application.security.SessionIdentity;
import com.routemind.business.domain.security.AuthenticatedPrincipal;
import java.util.Optional;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(name = "routemind.security.oidc.enabled", havingValue = "true")
public final class OidcCurrentSessionIdentity implements CurrentSessionIdentity {

	private final OidcPrincipalMapper principals;

	public OidcCurrentSessionIdentity(OidcPrincipalMapper principals) {
		this.principals = principals;
	}

	@Override
	public Optional<SessionIdentity> current() {
		Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
		if (!(authentication instanceof JwtAuthenticationToken jwt) || !authentication.isAuthenticated()) {
			return Optional.empty();
		}
		AuthenticatedPrincipal principal = principals.map(jwt.getToken());
		return Optional.of(new SessionIdentity(principal.subject(), principal.tenantId(), principal.roles(),
				principal.expiresAt()));
	}
}
