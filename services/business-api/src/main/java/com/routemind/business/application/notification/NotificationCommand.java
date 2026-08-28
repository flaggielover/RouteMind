package com.routemind.business.application.notification;

import com.routemind.business.domain.security.TenantId;
import java.time.Instant;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import java.util.regex.Pattern;

public record NotificationCommand(UUID notificationId, TenantId tenantId, UUID correlationId,
		String traceId, String idempotencyKey, NotificationChannel channel,
		NotificationRecipient recipient, NotificationSender sender, String templateId,
		Map<String, String> templateData, Instant requestedAt) {

	private static final Pattern IDEMPOTENCY_KEY = Pattern.compile("[A-Za-z0-9][A-Za-z0-9._:-]{0,127}");
	private static final Pattern TRACE_ID = Pattern.compile("[0-9a-f]{32}");

	public NotificationCommand {
		Objects.requireNonNull(notificationId, "notificationId");
		Objects.requireNonNull(tenantId, "tenantId");
		Objects.requireNonNull(correlationId, "correlationId");
		if (traceId == null || !TRACE_ID.matcher(traceId).matches()) {
			throw new IllegalArgumentException("traceId is invalid");
		}
		if (idempotencyKey == null || !IDEMPOTENCY_KEY.matcher(idempotencyKey).matches()) {
			throw new IllegalArgumentException("idempotencyKey is invalid");
		}
		Objects.requireNonNull(channel, "channel");
		Objects.requireNonNull(recipient, "recipient");
		Objects.requireNonNull(sender, "sender");
		if (templateId == null || templateId.isBlank() || templateId.length() > 128) {
			throw new IllegalArgumentException("templateId is invalid");
		}
		Objects.requireNonNull(templateData, "templateData");
		templateData = Map.copyOf(templateData);
		Objects.requireNonNull(requestedAt, "requestedAt");
	}
}
