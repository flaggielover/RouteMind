package com.routemind.business.infrastructure.security;

import java.net.URI;
import java.util.Locale;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("routemind.security.oidc")
public record OidcSecurityProperties(
		boolean enabled,
		URI issuer,
		String audience,
		URI jwkSetUri,
		String rolesClaim,
		boolean allowInsecureLoopback) {

	public OidcSecurityProperties {
		rolesClaim = rolesClaim == null || rolesClaim.isBlank() ? "roles" : safeText(rolesClaim, "rolesClaim");
		if (enabled) {
			if (issuer == null || jwkSetUri == null) {
				throw new IllegalArgumentException("OIDC issuer and JWK Set URI are required when OIDC is enabled");
			}
			audience = safeText(audience, "audience");
			validateEndpoint(issuer, "issuer", allowInsecureLoopback);
			validateEndpoint(jwkSetUri, "jwkSetUri", allowInsecureLoopback);
			if (!sameAuthority(issuer, jwkSetUri)) {
				throw new IllegalArgumentException("OIDC issuer and JWK Set URI must use the same authority");
			}
		}
	}

	private static void validateEndpoint(URI value, String name, boolean allowInsecureLoopback) {
		if (!value.isAbsolute() || value.getHost() == null || value.getUserInfo() != null || value.getFragment() != null) {
			throw new IllegalArgumentException(name + " must be an absolute URI without user info or fragment");
		}
		if ("https".equalsIgnoreCase(value.getScheme())) {
			return;
		}
		if (!allowInsecureLoopback || !"http".equalsIgnoreCase(value.getScheme()) || !isLoopback(value.getHost())) {
			throw new IllegalArgumentException(name + " must use HTTPS unless explicit loopback testing is enabled");
		}
	}

	private static boolean sameAuthority(URI left, URI right) {
		return left.getHost().equalsIgnoreCase(right.getHost())
				&& effectivePort(left) == effectivePort(right)
				&& left.getScheme().equalsIgnoreCase(right.getScheme());
	}

	private static int effectivePort(URI value) {
		if (value.getPort() >= 0) {
			return value.getPort();
		}
		return "https".equalsIgnoreCase(value.getScheme()) ? 443 : 80;
	}

	private static boolean isLoopback(String host) {
		String normalized = host.toLowerCase(Locale.ROOT);
		return normalized.equals("localhost") || normalized.equals("127.0.0.1") || normalized.equals("::1")
				|| normalized.equals("0:0:0:0:0:0:0:1");
	}

	private static String safeText(String value, String name) {
		if (value == null || value.isBlank() || value.chars().anyMatch(Character::isISOControl)) {
			throw new IllegalArgumentException(name + " must contain safe non-blank text");
		}
		return value.trim();
	}
}
