package com.routemind.business.application.notification;

@FunctionalInterface
public interface NotificationConsentChecker {

	NotificationConsent check(NotificationRequest request);
}
