package com.routemind.business.application.notification;

import java.util.Locale;
import java.util.Map;
import java.util.Set;

public final class NotificationPrivacyPolicy {

	public static final String REQUIRED_BOUNDARY = "EXTERNAL_NOTIFICATION_DATA_MINIMIZATION";
	private static final Set<String> ALLOWED_KEYS = Set.of("event_label", "status_label", "eta_label", "support_url");
	private static final Set<String> FORBIDDEN_TERMS = Set.of("order", "courier", "merchant", "customer", "payment",
			"phone", "email", "address", "tenant", "recipient", "sender", "credential", "secret");

	private NotificationPrivacyPolicy() {}

	public static void validate(Map<String, String> data) {
		if (data == null) throw new IllegalArgumentException("notification data is required");
		for (Map.Entry<String, String> entry : data.entrySet()) {
			String key = entry.getKey() == null ? "" : entry.getKey().toLowerCase(Locale.ROOT);
			if (!ALLOWED_KEYS.contains(key) || FORBIDDEN_TERMS.stream().anyMatch(key::contains)) {
				throw new IllegalArgumentException("notification data key is outside privacy boundary");
			}
			if (entry.getValue() == null || entry.getValue().isBlank() || entry.getValue().length() > 256) {
				throw new IllegalArgumentException("notification data value is invalid");
			}
		}
	}
}
