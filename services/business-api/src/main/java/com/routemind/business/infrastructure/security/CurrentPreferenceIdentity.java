package com.routemind.business.infrastructure.security;

import com.routemind.business.application.preference.PreferenceAccessDeniedException;
import com.routemind.business.application.preference.PreferenceIdentity;
import com.routemind.business.application.preference.PreferenceIdentityResolver;
import java.util.Locale;
import java.util.Set;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.stereotype.Component;

@Component
public final class CurrentPreferenceIdentity implements PreferenceIdentityResolver {

	private static final Set<String> ROLES = Set.of("customer", "courier", "merchant", "analyst", "operator");
	private final boolean oidcEnabled;

	public CurrentPreferenceIdentity(@Value("${routemind.security.oidc.enabled:false}") boolean oidcEnabled) {
		this.oidcEnabled = oidcEnabled;
	}

	public PreferenceIdentity resolve(String actor) {
		String role = normalizeRole(actor);
		if (!oidcEnabled) return new PreferenceIdentity("local:" + role, role);
		Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
		if (!(authentication instanceof JwtAuthenticationToken jwt) || !authentication.isAuthenticated()
				|| jwt.getToken().getSubject() == null
				|| authentication.getAuthorities().stream()
						.noneMatch(authority -> ("ROLE_" + role.toUpperCase(Locale.ROOT))
								.equals(authority.getAuthority()))) {
			throw new PreferenceAccessDeniedException();
		}
		return new PreferenceIdentity(jwt.getToken().getSubject(), role);
	}

	private static String normalizeRole(String actor) {
		if (actor == null || actor.isBlank()) throw new PreferenceAccessDeniedException();
		String normalized = actor.trim().toLowerCase(Locale.ROOT);
		if (!ROLES.contains(normalized)) throw new PreferenceAccessDeniedException();
		return normalized;
	}
}
