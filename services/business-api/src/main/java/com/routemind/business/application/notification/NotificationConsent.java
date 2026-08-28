package com.routemind.business.application.notification;

import java.util.Objects;

public record NotificationConsent(Decision decision, String reason) {

	public enum Decision { ALLOW, DEFER, SUPPRESS }

	public NotificationConsent {
		Objects.requireNonNull(decision, "decision");
		if (reason == null || reason.isBlank()) throw new IllegalArgumentException("consent reason is blank");
	}

	public static NotificationConsent allow() { return new NotificationConsent(Decision.ALLOW, "consent_allowed"); }
	public static NotificationConsent quietHours() { return new NotificationConsent(Decision.DEFER, "quiet_hours"); }
	public static NotificationConsent optOut() { return new NotificationConsent(Decision.SUPPRESS, "opt_out"); }
}
