package com.routemind.business.infrastructure.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Collections;
import java.util.Locale;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

public final class OidcActorBindingFilter extends OncePerRequestFilter {

	@Override
	protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
			throws ServletException, IOException {
		if (!request.getRequestURI().startsWith("/api/")) {
			filterChain.doFilter(request, response);
			return;
		}

		var actors = Collections.list(request.getHeaders("X-Actor"));
		if (actors.isEmpty()) {
			filterChain.doFilter(request, response);
			return;
		}
		if (actors.size() != 1 || !safe(actors.get(0))) {
			response.sendError(HttpServletResponse.SC_FORBIDDEN);
			return;
		}

		String requiredAuthority = "ROLE_" + actors.get(0).trim().toUpperCase(Locale.ROOT);
		Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
		boolean allowed = authentication != null && authentication.isAuthenticated()
				&& authentication.getAuthorities().stream()
						.anyMatch(authority -> requiredAuthority.equals(authority.getAuthority()));
		if (!allowed) {
			response.sendError(HttpServletResponse.SC_FORBIDDEN);
			return;
		}
		filterChain.doFilter(request, response);
	}

	private static boolean safe(String value) {
		return value != null && value.matches("[A-Za-z0-9][A-Za-z0-9._:-]{0,63}");
	}
}
