package com.routemind.business.infrastructure.security;

import com.routemind.business.domain.security.AuthenticatedPrincipal;
import com.routemind.business.domain.security.TenantId;
import java.util.Set;
import org.springframework.security.oauth2.jwt.Jwt;

public final class OidcPrincipalMapper {

	private final OidcSecurityProperties properties;

	public OidcPrincipalMapper(OidcSecurityProperties properties) {
		this.properties = properties;
	}

	public AuthenticatedPrincipal map(Jwt token) {
		Set<String> roles = OidcAuthorityConverter.claimValues(token.getClaims().get(properties.rolesClaim()));
		Set<String> scopes = OidcAuthorityConverter.claimValues(token.getClaims().get("scope"));
		return new AuthenticatedPrincipal(token.getSubject(), token.getIssuer().toString(), token.getId(),
				token.getIssuedAt(), token.getNotBefore() == null ? token.getIssuedAt() : token.getNotBefore(),
				token.getExpiresAt(), properties.audience(), roles, scopes,
				TenantId.parse(token.getClaimAsString(properties.tenantClaim())), true);
	}
}
