package com.routemind.business.application.notification;

import java.util.Objects;

public record NotificationResult(NotificationStatus status, int attempts, String failureClass,
		NotificationProvenance provenance) {

	public NotificationResult {
		Objects.requireNonNull(status, "status");
		if (attempts < 0) throw new IllegalArgumentException("attempts must not be negative");
		if (failureClass == null || failureClass.isBlank()) throw new IllegalArgumentException("failureClass is blank");
		Objects.requireNonNull(provenance, "provenance");
		if (status == NotificationStatus.DELIVERED && !provenance.authenticatedReceipt()) {
			throw new IllegalArgumentException("delivered requires authenticated receipt");
		}
	}

	public static NotificationResult accepted(NotificationRequest request, String provider, String region) {
		return accepted(request, provider, region, "send");
	}

	public static NotificationResult accepted(NotificationRequest request, String provider, String region,
			String operation) {
		return result(NotificationStatus.ACCEPTED, request, provider, region, operation, "ACCEPTED", false, "none");
	}

	public static NotificationResult delivered(NotificationRequest request, String provider, String region) {
		return result(NotificationStatus.DELIVERED, request, provider, region, "send", "DELIVERED", true, "none");
	}

	public static NotificationResult retryable(NotificationRequest request, String provider, String region,
			String failureClass) {
		return retryable(request, provider, region, failureClass, "send");
	}

	public static NotificationResult retryable(NotificationRequest request, String provider, String region,
			String failureClass, String operation) {
		return result(NotificationStatus.RETRYABLE, request, provider, region, operation, failureClass, false,
				failureClass);
	}

	public static NotificationResult suppressed(NotificationRequest request, String reason) {
		return result(NotificationStatus.SUPPRESSED, request, "local-policy", "LOCAL", "policy", reason, false, reason);
	}

	public static NotificationResult deadLetter(NotificationRequest request, String provider, String region,
			String failureClass) {
		return deadLetter(request, provider, region, failureClass, "send");
	}

	public static NotificationResult deadLetter(NotificationRequest request, String provider, String region,
			String failureClass, String operation) {
		return result(NotificationStatus.DEAD_LETTER, request, provider, region, operation, failureClass, false,
				failureClass);
	}

	private static NotificationResult result(NotificationStatus status, NotificationRequest request,
			String provider, String region, String operation, String outcome, boolean receipt, String failureClass) {
		return new NotificationResult(status, request.attempt(), failureClass,
				new NotificationProvenance(provider, region, operation, request.auditDigest(), outcome, receipt,
						java.time.Instant.now()));
	}
}
