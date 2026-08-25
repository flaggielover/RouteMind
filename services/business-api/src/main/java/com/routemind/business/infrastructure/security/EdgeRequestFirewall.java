package com.routemind.business.infrastructure.security;

import jakarta.servlet.http.HttpServletRequest;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.Locale;
import java.util.Set;

final class EdgeRequestFirewall {

	private static final Set<String> METHODS = Set.of("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD");
	private static final Set<String> BODY_METHODS = Set.of("POST", "PUT", "PATCH");

	private EdgeRequestFirewall() {
	}

	static FirewallDecision inspect(HttpServletRequest request, EdgeSecurityProperties policy) {
		String method = request.getMethod().toUpperCase(Locale.ROOT);
		if (!METHODS.contains(method)) {
			return FirewallDecision.reject("method_not_allowed");
		}
		String uri = request.getRequestURI();
		if (bytes(uri) > policy.maxPathBytes() || unsafePath(uri)) {
			return FirewallDecision.reject("unsafe_path");
		}
		String query = request.getQueryString();
		if (query != null && (bytes(query) > policy.maxQueryBytes() || hasControls(query))) {
			return FirewallDecision.reject("unsafe_query");
		}
		var names = request.getHeaderNames();
		if (names == null) {
			return FirewallDecision.reject("headers_unavailable");
		}
		int count = 0;
		int size = 0;
		for (String name : Collections.list(names)) {
			count++;
			size += bytes(name);
			for (String value : Collections.list(request.getHeaders(name))) {
				size += bytes(value);
				if (hasControls(value)) {
					return FirewallDecision.reject("unsafe_header");
				}
			}
		}
		if (count > policy.maxHeaderCount() || size > policy.maxHeaderBytes()) {
			return FirewallDecision.reject("header_limit");
		}
		if (multiple(request, "Host") || multiple(request, "Content-Length")) {
			return FirewallDecision.reject("ambiguous_header");
		}
		if (request.getHeader("Transfer-Encoding") != null && request.getHeader("Content-Length") != null) {
			return FirewallDecision.reject("request_smuggling_boundary");
		}
		long contentLength = request.getContentLengthLong();
		if (contentLength > policy.maxBodyBytes()) {
			return FirewallDecision.reject("body_limit");
		}
		if (contentLength > 0 && BODY_METHODS.contains(method)) {
			String contentType = request.getContentType();
			if (contentType == null || !contentType.toLowerCase(Locale.ROOT).startsWith("application/json")) {
				return FirewallDecision.reject("content_type_required");
			}
		}
		return FirewallDecision.allow();
	}

	static boolean requiresBoundedCapture(HttpServletRequest request) {
		return BODY_METHODS.contains(request.getMethod().toUpperCase(Locale.ROOT))
				&& request.getContentLengthLong() < 0;
	}

	private static boolean multiple(HttpServletRequest request, String name) {
		return Collections.list(request.getHeaders(name)).size() > 1;
	}

	private static boolean unsafePath(String value) {
		String lower = value.toLowerCase(Locale.ROOT);
		return hasControls(value) || value.indexOf('\\') >= 0 || lower.contains("..") || lower.contains("%00")
				|| lower.contains("%2e") || lower.contains("%5c") || lower.contains("%252e");
	}

	private static boolean hasControls(String value) {
		return value == null || value.chars().anyMatch(Character::isISOControl);
	}

	private static int bytes(String value) {
		return value == null ? 0 : value.getBytes(StandardCharsets.UTF_8).length;
	}

	record FirewallDecision(boolean allowed, String reason) {
		static FirewallDecision allow() {
			return new FirewallDecision(true, "admitted");
		}

		static FirewallDecision reject(String reason) {
			return new FirewallDecision(false, reason);
		}
	}
}
