package com.routemind.business.application.notification;

import java.time.Instant;
import java.util.Objects;
import java.util.regex.Pattern;

public record NotificationProvenance(String provider, String region, String operation,
		String requestDigest, String outcomeCode, boolean authenticatedReceipt, Instant observedAt) {

	private static final Pattern DIGEST = Pattern.compile("[0-9a-f]{64}");

	public NotificationProvenance {
		if (provider == null || provider.isBlank()) throw new IllegalArgumentException("provider is blank");
		if (region == null || region.isBlank()) throw new IllegalArgumentException("region is blank");
		if (operation == null || operation.isBlank()) throw new IllegalArgumentException("operation is blank");
		if (requestDigest == null || !DIGEST.matcher(requestDigest).matches()) {
			throw new IllegalArgumentException("requestDigest is invalid");
		}
		if (outcomeCode == null || outcomeCode.isBlank()) throw new IllegalArgumentException("outcomeCode is blank");
		Objects.requireNonNull(observedAt, "observedAt");
		if (!authenticatedReceipt && outcomeCode.equals("DELIVERED")) {
			throw new IllegalArgumentException("delivered requires authenticated receipt");
		}
	}
}
