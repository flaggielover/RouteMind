package com.routemind.business.application.notification;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;

import com.routemind.business.application.notification.mock.MockNotificationOutcome;
import com.routemind.business.application.notification.mock.MockNotificationProvider;
import com.routemind.business.domain.outbox.OutboxMessage;
import com.routemind.business.domain.security.TenantId;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

class NotificationDeliveryTests {

	private static final Instant REQUESTED_AT = Instant.parse("2026-08-28T12:00:00Z");
	private static final TenantId TENANT = new TenantId(UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"));
	private static final UUID NOTIFICATION_ID = UUID.fromString("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb");
	private static final UUID CORRELATION_ID = UUID.fromString("cccccccc-cccc-4ccc-8ccc-cccccccccccc");
	private static final NotificationRecipient RECIPIENT = new NotificationRecipient("synthetic-recipient@example.invalid");
	private static final NotificationSender SENDER = new NotificationSender("synthetic-sender@example.invalid");

	@Test
	void rendersDeclaredVariablesAndKeepsEndpointAndBodyOutOfAuditSurfaces() {
		NotificationCommand command = command(Map.of("status_label", "ready", "eta_label", "15 minutes"));
		NotificationTemplate template = new NotificationTemplate("dispatch-ready", NotificationChannel.EMAIL,
				"Route {{status_label}}", "ETA {{eta_label}}", java.util.Set.of("status_label", "eta_label"));

		NotificationRequest request = new NotificationTemplateRenderer().render(command, template);
		OutboxMessage outbox = NotificationOutbox.pending(command);

		assertThat(request.subject()).isEqualTo("Route ready");
		assertThat(request.body()).isEqualTo("ETA 15 minutes");
		assertThat(request.auditMetadata()).containsEntry("privacy_boundary",
				NotificationPrivacyPolicy.REQUIRED_BOUNDARY);
		assertThat(request.toString()).doesNotContain(RECIPIENT.address(), SENDER.address(), request.body());
		assertThat(outbox.event().eventType()).isEqualTo("notification.requested");
		assertThat(outbox.event().payload()).containsKeys("recipient_digest", "sender_digest", "privacy_boundary")
				.doesNotContainValue(RECIPIENT.address()).doesNotContainValue(SENDER.address());
		assertThat(outbox.event().payload().toString()).doesNotContain("ETA 15 minutes", "Route ready");
	}

	@Test
	void rejectsBusinessIdentifiersAtPrivacyBoundary() {
		assertThatIllegalArgumentException().isThrownBy(() -> NotificationPrivacyPolicy.validate(
				Map.of("order_id", "synthetic-order")));
		assertThatIllegalArgumentException().isThrownBy(() -> new NotificationTemplateRenderer().render(
				command(Map.of("status_label", "ok")),
				new NotificationTemplate("t", NotificationChannel.EMAIL, "{{status_label}}", "body",
						java.util.Set.of("status_label"))));
	}

	@Test
	void retriesTransientFailureThenReturnsDeliveredAndSuppressesDuplicate() {
		MockNotificationProvider provider = new MockNotificationProvider(
				List.of(MockNotificationOutcome.TIMEOUT, MockNotificationOutcome.DELIVERED));
		InMemoryNotificationDeliveryLedger ledger = new InMemoryNotificationDeliveryLedger();
		AtomicInteger sleeps = new AtomicInteger();
		NotificationRequest request = request();
		NotificationDeliveryWorker worker = new NotificationDeliveryWorker(provider, ledger,
				ignored -> NotificationConsent.allow(), 3, ignored -> sleeps.incrementAndGet());

		NotificationResult result = worker.deliver(request);
		NotificationResult duplicate = worker.deliver(request);

		assertThat(result.status()).isEqualTo(NotificationStatus.DELIVERED);
		assertThat(result.attempts()).isEqualTo(2);
		assertThat(result.provenance().authenticatedReceipt()).isTrue();
		assertThat(provider.calls()).hasSize(2);
		assertThat(provider.calls().get(0).attemptId()).isNotEqualTo(provider.calls().get(1).attemptId());
		assertThat(sleeps).hasValue(1);
		assertThat(duplicate).isEqualTo(result);
		assertThat(provider.calls()).hasSize(2);
	}

	@Test
	void exhaustsRetriesIntoDlqWithoutClaimingDelivery() {
		MockNotificationProvider provider = new MockNotificationProvider(
				List.of(MockNotificationOutcome.SERVER_ERROR, MockNotificationOutcome.RATE_LIMITED,
						MockNotificationOutcome.TRANSIENT_FAILURE));
		InMemoryNotificationDeliveryLedger ledger = new InMemoryNotificationDeliveryLedger();
		NotificationResult result = new NotificationDeliveryWorker(provider, ledger,
				ignored -> NotificationConsent.allow(), 3, ignored -> {}).deliver(request());

		assertThat(result.status()).isEqualTo(NotificationStatus.DEAD_LETTER);
		assertThat(result.provenance().authenticatedReceipt()).isFalse();
		assertThat(ledger.deadLetters()).containsExactly(result);
		assertThat(provider.calls()).hasSize(3);
	}

	@Test
	void consentSuppressesOrDefersBeforeProviderCall() {
		MockNotificationProvider suppressedProvider = new MockNotificationProvider(List.of(MockNotificationOutcome.DELIVERED));
		NotificationResult suppressed = new NotificationDeliveryWorker(suppressedProvider,
				new InMemoryNotificationDeliveryLedger(), ignored -> NotificationConsent.optOut(), 3, ignored -> {})
				.deliver(request());
		assertThat(suppressed.status()).isEqualTo(NotificationStatus.SUPPRESSED);
		assertThat(suppressedProvider.calls()).isEmpty();

		MockNotificationProvider deferredProvider = new MockNotificationProvider(List.of(MockNotificationOutcome.DELIVERED));
		AtomicInteger checks = new AtomicInteger();
		NotificationResult deferred = new NotificationDeliveryWorker(deferredProvider,
				new InMemoryNotificationDeliveryLedger(), ignored -> checks.getAndIncrement() == 0
						? NotificationConsent.quietHours() : NotificationConsent.allow(), 3, ignored -> {})
				.deliver(request());
		assertThat(deferred.status()).isEqualTo(NotificationStatus.DELIVERED);
		assertThat(checks).hasValue(2);
		assertThat(deferredProvider.calls()).hasSize(1);
	}

	@Test
	void mockProviderClassifiesEveryOfflineFailureOutcome() {
		for (MockNotificationOutcome outcome : MockNotificationOutcome.values()) {
			NotificationResult result = new MockNotificationProvider(List.of(outcome)).send(request());
			if (outcome == MockNotificationOutcome.DELIVERED) {
				assertThat(result.status()).isEqualTo(NotificationStatus.DELIVERED);
			}
			else if (outcome == MockNotificationOutcome.ACCEPTED) {
				assertThat(result.status()).isEqualTo(NotificationStatus.ACCEPTED);
			}
			else if (outcome == MockNotificationOutcome.TIMEOUT || outcome == MockNotificationOutcome.SERVER_ERROR
					|| outcome == MockNotificationOutcome.RATE_LIMITED || outcome == MockNotificationOutcome.TRANSIENT_FAILURE) {
				assertThat(result.status()).isEqualTo(NotificationStatus.RETRYABLE);
			}
			else {
				assertThat(result.status()).isEqualTo(NotificationStatus.DEAD_LETTER);
			}
		}
	}

	@Test
	void deliveredResultRequiresAuthenticatedReceipt() {
		assertThatIllegalArgumentException().isThrownBy(() -> new NotificationProvenance("mock", "LOCAL", "send",
				request().auditDigest(), "DELIVERED", false, REQUESTED_AT));
	}

	private static NotificationCommand command(Map<String, String> data) {
		return new NotificationCommand(NOTIFICATION_ID, TENANT, CORRELATION_ID,
				"0123456789abcdef0123456789abcdef", "notification-42", NotificationChannel.EMAIL,
				RECIPIENT, SENDER, "dispatch-ready", data, REQUESTED_AT);
	}

	private static NotificationRequest request() {
		return new NotificationTemplateRenderer().render(command(Map.of("status_label", "ready")),
				new NotificationTemplate("dispatch-ready", NotificationChannel.EMAIL,
						"Route ready", "Status {{status_label}}", java.util.Set.of("status_label")));
	}
}
