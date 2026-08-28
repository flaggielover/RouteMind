package com.routemind.business.application.notification;

import com.routemind.business.domain.security.TenantId;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.HexFormat;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

public final class NotificationRequest {

	private final UUID notificationId;
	private final TenantId tenantId;
	private final UUID correlationId;
	private final String idempotencyKey;
	private final NotificationChannel channel;
	private final NotificationRecipient recipient;
	private final NotificationSender sender;
	private final String templateId;
	private final String subject;
	private final String body;
	private final int attempt;
	private final UUID attemptId;
	private final Instant requestedAt;
	private final Map<String, String> auditMetadata;

	public NotificationRequest(UUID notificationId, TenantId tenantId, UUID correlationId,
			String idempotencyKey, NotificationChannel channel, NotificationRecipient recipient,
			NotificationSender sender, String templateId, String subject, String body, int attempt,
			UUID attemptId, Instant requestedAt, Map<String, String> auditMetadata) {
		this.notificationId = Objects.requireNonNull(notificationId, "notificationId");
		this.tenantId = Objects.requireNonNull(tenantId, "tenantId");
		this.correlationId = Objects.requireNonNull(correlationId, "correlationId");
		this.idempotencyKey = Objects.requireNonNull(idempotencyKey, "idempotencyKey");
		this.channel = Objects.requireNonNull(channel, "channel");
		this.recipient = Objects.requireNonNull(recipient, "recipient");
		this.sender = Objects.requireNonNull(sender, "sender");
		this.templateId = requireText(templateId, "templateId");
		this.subject = requireText(subject, "subject");
		this.body = requireText(body, "body");
		if (attempt < 1) throw new IllegalArgumentException("attempt must be positive");
		this.attempt = attempt;
		this.attemptId = Objects.requireNonNull(attemptId, "attemptId");
		this.requestedAt = Objects.requireNonNull(requestedAt, "requestedAt");
		this.auditMetadata = Map.copyOf(Objects.requireNonNull(auditMetadata, "auditMetadata"));
	}

	private static String requireText(String value, String field) {
		if (value == null || value.isBlank()) throw new IllegalArgumentException(field + " is blank");
		return value;
	}

	public UUID notificationId() { return notificationId; }
	public TenantId tenantId() { return tenantId; }
	public UUID correlationId() { return correlationId; }
	public String idempotencyKey() { return idempotencyKey; }
	public NotificationChannel channel() { return channel; }
	public NotificationRecipient recipient() { return recipient; }
	public NotificationSender sender() { return sender; }
	public String templateId() { return templateId; }
	public String subject() { return subject; }
	public String body() { return body; }
	public int attempt() { return attempt; }
	public UUID attemptId() { return attemptId; }
	public Instant requestedAt() { return requestedAt; }
	public Map<String, String> auditMetadata() { return auditMetadata; }

	public NotificationRequest forAttempt(int nextAttempt) {
		UUID nextId = UUID.nameUUIDFromBytes((idempotencyKey + ":" + nextAttempt)
				.getBytes(StandardCharsets.UTF_8));
		return new NotificationRequest(notificationId, tenantId, correlationId, idempotencyKey, channel,
				recipient, sender, templateId, subject, body, nextAttempt, nextId, requestedAt, auditMetadata);
	}

	/** Digest is deliberately limited to non-content metadata and redacted endpoint digests. */
	public String auditDigest() {
		String canonical = notificationId + "|" + tenantId.value() + "|" + correlationId + "|"
				+ idempotencyKey + "|" + channel + "|" + templateId + "|" + recipient.digest() + "|"
				+ sender.digest();
		try {
			return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
					.digest(canonical.getBytes(StandardCharsets.UTF_8)));
		}
		catch (NoSuchAlgorithmException exception) {
			throw new IllegalStateException("SHA-256 is unavailable", exception);
		}
	}

	@Override
	public String toString() {
		return "NotificationRequest{id=" + notificationId + ", template=" + templateId
				+ ", attempt=" + attempt + ", recipientDigest=" + recipient.digest().substring(0, 16)
				+ "}";
	}
}
