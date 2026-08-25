package com.routemind.business.infrastructure.security;

import java.util.Collection;
import java.util.Locale;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.security.core.GrantedAuthority;

@ConfigurationProperties("routemind.security.edge")
public record EdgeSecurityProperties(
		boolean enabled,
		String policyVersion,
		long windowSeconds,
		long burstAllowance,
		long anonymousRequests,
		long authenticatedRequests,
		long customerRequests,
		long courierRequests,
		long merchantRequests,
		long analystRequests,
		long operatorRequests,
		int maxTrackedKeys,
		int maxHeaderCount,
		int maxHeaderBytes,
		int maxQueryBytes,
		int maxPathBytes,
		long maxBodyBytes) {

	public EdgeSecurityProperties {
		policyVersion = safeText(policyVersion, "policyVersion");
		if (windowSeconds <= 0 || burstAllowance < 0 || anonymousRequests <= 0 || authenticatedRequests <= 0
				|| customerRequests <= 0 || courierRequests <= 0 || merchantRequests <= 0 || analystRequests <= 0
				|| operatorRequests <= 0 || maxTrackedKeys <= 0 || maxHeaderCount <= 0 || maxHeaderBytes <= 0
				|| maxQueryBytes <= 0 || maxPathBytes <= 0 || maxBodyBytes <= 0) {
			throw new IllegalArgumentException("edge security limits must be positive");
		}
		if (maxBodyBytes >= Integer.MAX_VALUE) {
			throw new IllegalArgumentException("edge security body limit must fit in a bounded request buffer");
		}
		long largestQuota = Math.max(Math.max(Math.max(anonymousRequests, authenticatedRequests),
				Math.max(customerRequests, courierRequests)),
				Math.max(Math.max(merchantRequests, analystRequests), operatorRequests));
		if (largestQuota > Long.MAX_VALUE - burstAllowance) {
			throw new IllegalArgumentException("edge security quota and burst overflow");
		}
	}

	RoleLimit roleLimit(Collection<? extends GrantedAuthority> authorities, boolean authenticated) {
		if (!authenticated) {
			return new RoleLimit("anonymous", anonymousRequests);
		}
		RoleLimit selected = null;
		for (GrantedAuthority authority : authorities) {
			String value = authority.getAuthority().toUpperCase(Locale.ROOT);
			RoleLimit candidate = switch (value) {
				case "ROLE_CUSTOMER" -> new RoleLimit("customer", customerRequests);
				case "ROLE_COURIER" -> new RoleLimit("courier", courierRequests);
				case "ROLE_MERCHANT" -> new RoleLimit("merchant", merchantRequests);
				case "ROLE_ANALYST" -> new RoleLimit("analyst", analystRequests);
				case "ROLE_OPERATOR" -> new RoleLimit("operator", operatorRequests);
				default -> null;
			};
			if (candidate != null && (selected == null || candidate.requests() > selected.requests())) {
				selected = candidate;
			}
		}
		return selected == null ? new RoleLimit("authenticated", authenticatedRequests) : selected;
	}

	record RoleLimit(String role, long requests) {
	}

	private static String safeText(String value, String name) {
		if (value == null || value.isBlank() || value.chars().anyMatch(Character::isISOControl)) {
			throw new IllegalArgumentException(name + " must contain safe non-blank text");
		}
		return value.trim();
	}
}
