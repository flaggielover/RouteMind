package com.routemind.business.infrastructure.security;

import com.routemind.business.application.security.TenantContext;
import com.routemind.business.application.observability.TelemetryAttribution;
import com.routemind.business.domain.security.TenantId;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Collections;
import java.util.Objects;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.web.filter.OncePerRequestFilter;

public final class TenantContextFilter extends OncePerRequestFilter {

	private static final String LOCAL_HEADER = "X-Tenant-Id";
	private final TenantContext tenants;
	private final String tenantClaim;
	private final boolean localMode;
	private final TelemetryAttribution telemetry;

	private TenantContextFilter(TenantContext tenants, String tenantClaim, boolean localMode,
			TelemetryAttribution telemetry) {
		this.tenants = Objects.requireNonNull(tenants, "tenants");
		this.tenantClaim = tenantClaim;
		this.localMode = localMode;
		this.telemetry = Objects.requireNonNull(telemetry, "telemetry");
	}

	static TenantContextFilter oidc(TenantContext tenants, String tenantClaim,
			TelemetryAttribution telemetry) {
		return new TenantContextFilter(tenants, Objects.requireNonNull(tenantClaim, "tenantClaim"), false,
				telemetry);
	}

	static TenantContextFilter local(TenantContext tenants, TelemetryAttribution telemetry) {
		return new TenantContextFilter(tenants, null, true, telemetry);
	}

	@Override
	protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
			throws ServletException, IOException {
		if (!request.getRequestURI().startsWith("/api/") && !request.getRequestURI().equals("/metrics")) {
			chain.doFilter(request, response);
			return;
		}
		try {
			TenantId tenant = localMode ? localTenant(request) : oidcTenant(request);
			if (tenant == null) {
				chain.doFilter(request, response);
				return;
			}
			request.setAttribute(TelemetryAttribution.REQUEST_ATTRIBUTE,
					telemetry.tenantKey(tenant.value()));
			try (TenantContext.Scope ignored = tenants.open(tenant)) {
				chain.doFilter(request, response);
			}
		}
		catch (IllegalArgumentException exception) {
			response.sendError(HttpServletResponse.SC_FORBIDDEN);
		}
	}

	private TenantId oidcTenant(HttpServletRequest request) {
		if (request.getHeader(LOCAL_HEADER) != null) {
			throw new IllegalArgumentException("tenant header is forbidden with OIDC");
		}
		Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
		if (authentication == null || !authentication.isAuthenticated()) {
			return null;
		}
		if (!(authentication instanceof JwtAuthenticationToken jwt)) {
			throw new IllegalArgumentException("verified JWT identity is required");
		}
		Object value = jwt.getToken().getClaims().get(tenantClaim);
		if (!(value instanceof String tenant)) {
			throw new IllegalArgumentException("verified tenant claim is required");
		}
		return TenantId.parse(tenant);
	}

	private static TenantId localTenant(HttpServletRequest request) {
		var values = Collections.list(request.getHeaders(LOCAL_HEADER));
		if (values.isEmpty()) {
			return TenantId.LEGACY;
		}
		if (values.size() != 1) {
			throw new IllegalArgumentException("exactly one tenant header is allowed");
		}
		return TenantId.parse(values.get(0));
	}
}
