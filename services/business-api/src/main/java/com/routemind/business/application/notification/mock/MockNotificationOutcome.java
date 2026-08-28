package com.routemind.business.application.notification.mock;

public enum MockNotificationOutcome {
	ACCEPTED,
	DELIVERED,
	TIMEOUT,
	CLIENT_ERROR,
	SERVER_ERROR,
	RATE_LIMITED,
	MALFORMED_RESPONSE,
	TRANSIENT_FAILURE,
	PERMANENT_FAILURE
}
