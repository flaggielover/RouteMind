package com.routemind.business.infrastructure.notification;

import java.text.Normalizer;
import java.util.Locale;

/** Structural endpoint observations only; the inspected value is never retained. */
public record SesEndpointValueAudit(boolean present, boolean nonBlank, Comparison exactApprovedMatch,
		Comparison trimmedApprovedMatch, boolean rawEqualsNormalized, boolean trimmedEqualsNormalized,
		boolean leadingOrTrailingWhitespace, boolean displayNameSyntax, boolean angleBracketSyntax,
		boolean unicodeNormalizationDifference, boolean caseNormalizationChangesValue) {

	public enum Comparison {
		MATCH,
		MISMATCH,
		COMPARISON_INPUT_UNAVAILABLE
	}

	public static SesEndpointValueAudit inspect(String rawValue, String normalizedValue, String approvedValue) {
		boolean present = rawValue != null;
		String raw = rawValue == null ? "" : rawValue;
		String trimmed = raw.trim();
		return new SesEndpointValueAudit(
				present,
				!raw.isBlank(),
				compare(raw, approvedValue),
				compare(trimmed, approvedValue),
				normalizedValue != null && raw.equals(normalizedValue),
				normalizedValue != null && trimmed.equals(normalizedValue),
				!raw.equals(trimmed),
				hasDisplayNameSyntax(raw),
				raw.indexOf('<') >= 0 || raw.indexOf('>') >= 0,
				!Normalizer.normalize(raw, Normalizer.Form.NFC).equals(raw),
				!raw.toLowerCase(Locale.ROOT).equals(raw));
	}

	private static Comparison compare(String actual, String approved) {
		if (approved == null) return Comparison.COMPARISON_INPUT_UNAVAILABLE;
		return actual.equals(approved) ? Comparison.MATCH : Comparison.MISMATCH;
	}

	private static boolean hasDisplayNameSyntax(String value) {
		int open = value.indexOf('<');
		int close = value.indexOf('>');
		return open > 0 && close > open;
	}
}
