package com.routemind.business.domain.security;

public record RequestDescriptor(String method, String endpoint, String key, long bodyBytes, int fieldCount,
		int longestFieldLength, boolean validUtf8, boolean containsControlCharacters, boolean command,
		boolean idempotencyKeyPresent) {

	public RequestDescriptor {
		method = text(method, "method");
		endpoint = text(endpoint, "endpoint");
		key = text(key, "key");
		if (bodyBytes < 0 || fieldCount < 0 || longestFieldLength < 0) {
			throw new IllegalArgumentException("request measurements must be non-negative");
		}
	}

	private static String text(String value, String name) {
		if (value == null || value.isBlank()) {
			throw new IllegalArgumentException(name + " must not be blank");
		}
		return value.trim();
	}
}
