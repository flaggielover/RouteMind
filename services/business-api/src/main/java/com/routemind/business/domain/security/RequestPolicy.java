package com.routemind.business.domain.security;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

public record RequestPolicy(String policyVersion, RequestPolicyScope scope, long windowSeconds, long maxRequests,
		long burstAllowance, long maxBodyBytes, int maxFields, int maxFieldLength) {

	public RequestPolicy {
		policyVersion = text(policyVersion, "policyVersion");
		if (scope == null) {
			throw new NullPointerException("scope must not be null");
		}
		if (windowSeconds <= 0 || maxRequests <= 0 || burstAllowance < 0 || maxBodyBytes < 0 || maxFields <= 0
				|| maxFieldLength <= 0) {
			throw new IllegalArgumentException("request limits are invalid");
		}
	}

	public String digest() {
		String canonical = String.join("|", policyVersion, scope.name(), Long.toString(windowSeconds),
				Long.toString(maxRequests), Long.toString(burstAllowance), Long.toString(maxBodyBytes),
				Integer.toString(maxFields), Integer.toString(maxFieldLength));
		try {
			MessageDigest digest = MessageDigest.getInstance("SHA-256");
			byte[] bytes = digest.digest(canonical.getBytes(StandardCharsets.UTF_8));
			StringBuilder result = new StringBuilder(bytes.length * 2);
			for (byte value : bytes) {
				result.append(String.format("%02x", value));
			}
			return result.toString();
		}
		catch (NoSuchAlgorithmException exception) {
			throw new IllegalStateException("SHA-256 is unavailable", exception);
		}
	}

	private static String text(String value, String name) {
		if (value == null || value.isBlank()) {
			throw new IllegalArgumentException(name + " must not be blank");
		}
		return value.trim();
	}
}
