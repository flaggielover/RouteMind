package com.routemind.business.infrastructure.notification;

import java.time.Instant;
import java.util.Objects;
import java.util.regex.Pattern;

/** Sanitized Gmail provider outcome; raw Google error payloads are never retained. */
public record GoogleGmailErrorObservation(String provider, String operation, String region,
		int httpStatus, Category category, String safeReason, boolean providerAcceptance,
		int requestCount, int retryCount, boolean fallbackUsed, boolean messageIdPresent,
		Instant observedAt) {

	private static final Pattern SAFE_REASON = Pattern.compile("[A-Z0-9_]{1,64}");

	public enum Category {
		ACCEPTED,
		AUTHENTICATION_REJECTED,
		AUTHORIZATION_REJECTED,
		RATE_LIMITED,
		INVALID_REQUEST,
		PROVIDER_SERVER_FAILURE,
		PROVIDER_UNAVAILABLE,
		TIMEOUT,
		UNKNOWN_PROVIDER_FAILURE
	}

	public GoogleGmailErrorObservation {
		if (!"GOOGLE_GMAIL_API".equals(provider)) throw new IllegalArgumentException("provider is invalid");
		if (!"users.messages.send".equals(operation)) throw new IllegalArgumentException("operation is invalid");
		if (region == null || region.isBlank() || region.length() > 32) throw new IllegalArgumentException("region is invalid");
		if (httpStatus < 0 || httpStatus > 599) throw new IllegalArgumentException("httpStatus is invalid");
		Objects.requireNonNull(category, "category");
		if (safeReason == null || !SAFE_REASON.matcher(safeReason).matches()) throw new IllegalArgumentException("safeReason is invalid");
		if (providerAcceptance && category != Category.ACCEPTED) {
			throw new IllegalArgumentException("only ACCEPTED may claim provider acceptance");
		}
		if (!providerAcceptance && category == Category.ACCEPTED) {
			throw new IllegalArgumentException("ACCEPTED requires provider acceptance");
		}
		if (requestCount != 1 || retryCount != 0 || fallbackUsed) throw new IllegalArgumentException("bounded outcome counters invalid");
		Objects.requireNonNull(observedAt, "observedAt");
	}

	public static GoogleGmailErrorObservation fromStatus(int status, String reason, String region,
			Instant observedAt) {
		Category category = switch (status) {
			case 401 -> Category.AUTHENTICATION_REJECTED;
			case 403 -> Category.AUTHORIZATION_REJECTED;
			case 429 -> Category.RATE_LIMITED;
			default -> status >= 500 ? Category.PROVIDER_SERVER_FAILURE : Category.INVALID_REQUEST;
		};
		return new GoogleGmailErrorObservation("GOOGLE_GMAIL_API", "users.messages.send", region, status,
				category, normalizeReason(reason), false, 1, 0, false, false, observedAt);
	}

	public static GoogleGmailErrorObservation accepted(String region, boolean messageIdPresent,
			Instant observedAt) {
		return new GoogleGmailErrorObservation("GOOGLE_GMAIL_API", "users.messages.send", region, 200,
				Category.ACCEPTED, "ACCEPTED", true, 1, 0, false, messageIdPresent, observedAt);
	}

	public static GoogleGmailErrorObservation clientFailure(Category category, String region, Instant observedAt) {
		if (category != Category.PROVIDER_UNAVAILABLE && category != Category.TIMEOUT
				&& category != Category.UNKNOWN_PROVIDER_FAILURE) {
			throw new IllegalArgumentException("invalid client failure category");
		}
		return new GoogleGmailErrorObservation("GOOGLE_GMAIL_API", "users.messages.send", region, 0,
				category, category.name(), false, 1, 0, false, false, observedAt);
	}

	private static String normalizeReason(String reason) {
		if (reason == null || reason.isBlank()) return "UNAVAILABLE";
		String normalized = reason.trim().toUpperCase().replaceAll("[^A-Z0-9_]", "_");
		return SAFE_REASON.matcher(normalized).matches() ? normalized : "UNAVAILABLE";
	}
}
