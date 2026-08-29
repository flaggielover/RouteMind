package com.routemind.business.infrastructure.notification;

import com.google.api.client.auth.oauth2.AuthorizationCodeRequestUrl;
import com.google.api.client.googleapis.auth.oauth2.GoogleAuthorizationCodeFlow;
import java.net.URI;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;

/** In-memory readiness and single-callback state for the V2 bootstrap. */
final class GmailOAuthBootstrapV2Session {

	static final String PREFLIGHT_PATH = "/routemind-oauth-preflight";
	static final String CALLBACK_PATH = "/oauth2callback";
	static final String PREFLIGHT_RESPONSE = "ROUTEMIND_GMAIL_OAUTH_TUNNEL_READY";

	private String expectedState;
	private boolean preflightPassed;
	private boolean callbackConsumed;
	private boolean terminalFailure;

	GmailOAuthBootstrapV2Session() {
	}

	private static String newState() {
		byte[] stateBytes = new byte[32];
		new SecureRandom().nextBytes(stateBytes);
		return Base64.getUrlEncoder().withoutPadding().encodeToString(stateBytes);
	}

	synchronized String expectedState() {
		if (expectedState == null) {
			throw new IllegalStateException("OAuth state is not initialized");
		}
		return expectedState;
	}

	synchronized void recordPreflight() {
		if (terminalFailure || preflightPassed) {
			terminalFailure = true;
			throw new IllegalStateException("duplicate OAuth tunnel preflight");
		}
		preflightPassed = true;
	}

	synchronized boolean preflightPassed() {
		return preflightPassed;
	}

	synchronized void fail(String reason) {
		if (reason == null || reason.isBlank()) {
			throw new IllegalArgumentException("failure reason is required");
		}
		terminalFailure = true;
	}

	synchronized boolean terminalFailure() {
		return terminalFailure;
	}

	synchronized boolean authorizationUrlEligible() {
		return preflightPassed && !terminalFailure;
	}

	synchronized void activateAuthorization() {
		if (!authorizationUrlEligible()) {
			throw new IllegalStateException("OAuth authorization requires tunnel preflight");
		}
		if (expectedState == null) {
			expectedState = newState();
		}
	}

	AuthorizationCodeRequestUrl authorizationUrl(GoogleAuthorizationCodeFlow flow, String redirectUri) {
		Objects.requireNonNull(flow, "flow");
		if (terminalFailure()) {
			throw new IllegalStateException("OAuth bootstrap session is terminal");
		}
		if (!authorizationUrlEligible()) {
			throw new IllegalStateException("OAuth authorization URL requires tunnel preflight");
		}
		activateAuthorization();
		return GoogleGmailOAuthBootstrap.authorizationUrl(flow, redirectUri).set("state", expectedState);
	}

	synchronized Callback callback(URI requestUri) {
		Objects.requireNonNull(requestUri, "requestUri");
		if (terminalFailure) {
			return Callback.rejected("OAuth bootstrap session is terminal");
		}
		if (!CALLBACK_PATH.equals(requestUri.getPath())) {
			return Callback.rejected("unexpected callback path");
		}
		if (!preflightPassed) {
			return Callback.rejected("tunnel preflight is incomplete");
		}
		if (expectedState == null) {
			return Callback.rejected("OAuth state is not initialized");
		}
		if (callbackConsumed) {
			return Callback.rejected("duplicate OAuth callback");
		}
		Map<String, String> parameters;
		try {
			parameters = parseQuery(requestUri.getRawQuery());
		}
		catch (IllegalArgumentException exception) {
			terminalFailure = true;
			throw exception;
		}
		String state = parameters.get("state");
		if (!expectedState.equals(state)) {
			terminalFailure = true;
			return Callback.rejected("OAuth state mismatch");
		}
		String error = parameters.get("error");
		if (error != null && !error.isBlank()) {
			callbackConsumed = true;
			terminalFailure = true;
			return Callback.rejected("OAuth authorization returned an error");
		}
		String code = parameters.get("code");
		if (code == null || code.isBlank()) {
			terminalFailure = true;
			return Callback.rejected("OAuth authorization code is missing");
		}
		callbackConsumed = true;
		return Callback.accepted(code);
	}

	private static Map<String, String> parseQuery(String query) {
		Map<String, String> values = new HashMap<>();
		if (query == null || query.isBlank()) {
			return values;
		}
		for (String pair : query.split("&", -1)) {
			String[] parts = pair.split("=", 2);
			String key = decode(parts[0]);
			if (!(key.equals("state") || key.equals("code") || key.equals("error"))) {
				continue;
			}
			if (values.containsKey(key)) {
				throw new IllegalArgumentException("duplicate OAuth callback parameter");
			}
			values.put(key, parts.length == 2 ? decode(parts[1]) : "");
		}
		return values;
	}

	private static String decode(String value) {
		return URLDecoder.decode(value, StandardCharsets.UTF_8);
	}

	record Callback(boolean accepted, String code, String rejectionReason) {
		static Callback accepted(String code) {
			return new Callback(true, code, "");
		}

		static Callback rejected(String reason) {
			return new Callback(false, "", reason);
		}
	}
}
