package com.routemind.business.application.notification;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

public final class InMemoryNotificationDeliveryLedger implements NotificationDeliveryLedger {

	private final Map<String, NotificationResult> completed = new HashMap<>();
	private final Set<String> inFlight = new HashSet<>();
	private final List<NotificationResult> deadLetters = new ArrayList<>();

	@Override
	public synchronized Optional<NotificationResult> completed(String idempotencyKey) {
		return Optional.ofNullable(completed.get(idempotencyKey));
	}

	@Override
	public synchronized boolean begin(String idempotencyKey) {
		if (completed.containsKey(idempotencyKey) || !inFlight.add(idempotencyKey)) return false;
		return true;
	}

	@Override
	public synchronized void complete(String idempotencyKey, NotificationResult result) {
		inFlight.remove(idempotencyKey);
		completed.put(idempotencyKey, result);
		if (result.status() == NotificationStatus.DEAD_LETTER) deadLetters.add(result);
	}

	@Override
	public synchronized List<NotificationResult> deadLetters() {
		return List.copyOf(deadLetters);
	}
}
