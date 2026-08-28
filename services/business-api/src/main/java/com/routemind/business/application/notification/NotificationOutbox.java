package com.routemind.business.application.notification;

import com.routemind.business.domain.event.EventEnvelope;
import com.routemind.business.domain.outbox.OutboxMessage;
import java.util.Map;

public final class NotificationOutbox {

	private NotificationOutbox() {}

	public static OutboxMessage pending(NotificationCommand command) {
		EventEnvelope event = new EventEnvelope("1.0", command.notificationId(), "notification.requested",
				command.requestedAt(), "business-api", command.tenantId().value(), command.notificationId(), 1,
				command.correlationId(), null, command.traceId(), Map.of(
						"notification_id", command.notificationId().toString(),
						"channel", command.channel().name(),
						"template_id", command.templateId(),
						"idempotency_key", command.idempotencyKey(),
						"recipient_digest", command.recipient().digest(),
						"sender_digest", command.sender().digest(),
						"privacy_boundary", NotificationPrivacyPolicy.REQUIRED_BOUNDARY));
		return OutboxMessage.pending(event);
	}
}
