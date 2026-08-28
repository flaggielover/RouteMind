package com.routemind.business.application.notification.mock;

import com.routemind.business.application.notification.NotificationProvider;
import com.routemind.business.application.notification.NotificationRequest;
import com.routemind.business.application.notification.NotificationResult;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;

/** Offline-only provider for deterministic failure and recovery tests. */
public final class MockNotificationProvider implements NotificationProvider {

	private final Deque<MockNotificationOutcome> outcomes;
	private final List<NotificationRequest> calls = new ArrayList<>();

	public MockNotificationProvider(List<MockNotificationOutcome> outcomes) {
		this.outcomes = new ArrayDeque<>(outcomes);
	}

	@Override
	public NotificationResult send(NotificationRequest request) {
		calls.add(request);
		MockNotificationOutcome outcome = outcomes.isEmpty() ? MockNotificationOutcome.ACCEPTED : outcomes.removeFirst();
		return switch (outcome) {
			case ACCEPTED -> NotificationResult.accepted(request, "mock-notification", "LOCAL");
			case DELIVERED -> NotificationResult.delivered(request, "mock-notification", "LOCAL");
			case TIMEOUT -> NotificationResult.retryable(request, "mock-notification", "LOCAL", "timeout");
			case SERVER_ERROR, RATE_LIMITED, TRANSIENT_FAILURE -> NotificationResult.retryable(request,
					"mock-notification", "LOCAL", outcome.name().toLowerCase());
			case CLIENT_ERROR, MALFORMED_RESPONSE, PERMANENT_FAILURE -> NotificationResult.deadLetter(request,
					"mock-notification", "LOCAL", outcome.name().toLowerCase());
		};
	}

	public List<NotificationRequest> calls() { return List.copyOf(calls); }
}
