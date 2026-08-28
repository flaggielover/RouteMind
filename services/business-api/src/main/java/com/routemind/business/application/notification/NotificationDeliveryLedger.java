package com.routemind.business.application.notification;

import java.util.List;
import java.util.Optional;

public interface NotificationDeliveryLedger {

	Optional<NotificationResult> completed(String idempotencyKey);

	boolean begin(String idempotencyKey);

	void complete(String idempotencyKey, NotificationResult result);

	List<NotificationResult> deadLetters();
}
