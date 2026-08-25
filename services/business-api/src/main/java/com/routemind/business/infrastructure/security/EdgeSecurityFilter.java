package com.routemind.business.infrastructure.security;

import com.routemind.business.application.security.TenantContext;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Clock;
import java.util.HexFormat;
import java.util.Locale;
import java.util.Objects;
import java.util.regex.Pattern;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

public final class EdgeSecurityFilter extends OncePerRequestFilter {

	private static final Pattern UUID_SEGMENT = Pattern.compile(
			"(?i)(?<=/)[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?=/|$)");
	private static final Pattern NUMBER_SEGMENT = Pattern.compile("(?<=/)\\d+(?=/|$)");
	private final TenantContext tenants;
	private final EdgeSecurityProperties policy;
	private final ResilientEdgeRateLimiter limiter;
	private final Clock clock;

	EdgeSecurityFilter(TenantContext tenants, EdgeSecurityProperties policy, ResilientEdgeRateLimiter limiter,
			Clock clock) {
		this.tenants = Objects.requireNonNull(tenants, "tenants");
		this.policy = Objects.requireNonNull(policy, "policy");
		this.limiter = Objects.requireNonNull(limiter, "limiter");
		this.clock = Objects.requireNonNull(clock, "clock");
	}

	@Override
	protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
			throws ServletException, IOException {
		if (!policy.enabled() || !protectedPath(request.getRequestURI())) {
			chain.doFilter(request, response);
			return;
		}
		response.setHeader("X-Edge-Policy", policy.policyVersion());
		EdgeRequestFirewall.FirewallDecision firewall = EdgeRequestFirewall.inspect(request, policy);
		if (!firewall.allowed()) {
			response.setHeader("X-Edge-Decision", firewall.reason());
			response.sendError(HttpServletResponse.SC_BAD_REQUEST);
			return;
		}
		HttpServletRequest admittedRequest = request;
		if (EdgeRequestFirewall.requiresBoundedCapture(request)) {
			try {
				admittedRequest = BoundedBodyHttpServletRequest.capture(request, policy.maxBodyBytes());
			}
			catch (BoundedBodyHttpServletRequest.BodyLimitExceededException exception) {
				response.setHeader("X-Edge-Decision", "body_limit");
				response.sendError(HttpServletResponse.SC_REQUEST_ENTITY_TOO_LARGE);
				return;
			}
			firewall = EdgeRequestFirewall.inspect(admittedRequest, policy);
			if (!firewall.allowed()) {
				response.setHeader("X-Edge-Decision", firewall.reason());
				response.sendError(HttpServletResponse.SC_BAD_REQUEST);
				return;
			}
		}

		Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
		boolean authenticated = authentication != null && authentication.isAuthenticated()
				&& !"anonymousUser".equals(authentication.getPrincipal());
		var role = policy.roleLimit(authenticated ? authentication.getAuthorities() : java.util.List.of(), authenticated);
		long capacity = Math.addExact(role.requests(), policy.burstAllowance());
		String actor = authenticated ? authentication.getName() : request.getRemoteAddr();
		actor = actor == null || actor.isBlank() ? "unavailable" : actor;
		String key = digest(String.join("|", policy.policyVersion(), tenants.current().value().toString(), role.role(), actor,
				request.getMethod().toUpperCase(Locale.ROOT), routeTemplate(request.getRequestURI())));
		var decision = limiter.consume(key, clock.instant(), policy.windowSeconds(), capacity);
		response.setHeader("X-RateLimit-Limit", Long.toString(capacity));
		response.setHeader("X-RateLimit-Remaining", Long.toString(decision.remaining()));
		response.setHeader("X-RateLimit-Mode", decision.mode());
		if (decision.unavailable()) {
			response.setHeader("Retry-After", Long.toString(decision.retryAfterSeconds()));
			response.sendError(HttpServletResponse.SC_SERVICE_UNAVAILABLE);
			return;
		}
		if (!decision.allowed()) {
			response.setHeader("Retry-After", Long.toString(decision.retryAfterSeconds()));
			response.sendError(429);
			return;
		}
		chain.doFilter(admittedRequest, response);
	}

	private static boolean protectedPath(String uri) {
		return uri.startsWith("/api/") || uri.equals("/metrics");
	}

	private static String routeTemplate(String uri) {
		return NUMBER_SEGMENT.matcher(UUID_SEGMENT.matcher(uri).replaceAll(":id")).replaceAll(":id");
	}

	private static String digest(String value) {
		try {
			return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
					.digest(value.getBytes(StandardCharsets.UTF_8)));
		}
		catch (NoSuchAlgorithmException exception) {
			throw new IllegalStateException("SHA-256 is unavailable", exception);
		}
	}
}
