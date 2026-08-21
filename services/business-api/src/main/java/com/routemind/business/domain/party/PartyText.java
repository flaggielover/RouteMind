package com.routemind.business.domain.party;

import java.util.regex.Pattern;

final class PartyText {

	private static final Pattern EXTERNAL_REFERENCE = Pattern.compile("[A-Za-z0-9][A-Za-z0-9._:-]{0,63}");

	private PartyText() {
	}

	static String externalReference(String value) {
		String normalized = text(value, "externalReference", 64);
		if (!EXTERNAL_REFERENCE.matcher(normalized).matches()) {
			throw new IllegalArgumentException("externalReference contains unsupported characters");
		}
		return normalized;
	}

	static String displayName(String value) {
		String normalized = text(value, "displayName", 120);
		if (normalized.chars().anyMatch(Character::isISOControl)) {
			throw new IllegalArgumentException("displayName must not contain control characters");
		}
		return normalized;
	}

	private static String text(String value, String field, int maximumLength) {
		if (value == null || value.isBlank()) {
			throw new IllegalArgumentException(field + " must not be blank");
		}
		String normalized = value.trim();
		if (normalized.length() > maximumLength) {
			throw new IllegalArgumentException(field + " must not exceed " + maximumLength + " characters");
		}
		return normalized;
	}
}
