package com.routemind.business.infrastructure.notification;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.routemind.business.application.notification.NotificationChannel;
import com.routemind.business.application.notification.NotificationRecipient;
import com.routemind.business.application.notification.NotificationRequest;
import com.routemind.business.application.notification.NotificationSender;
import com.routemind.business.domain.security.TenantId;
import jakarta.mail.Session;
import jakarta.mail.internet.MimeMessage;
import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

class GoogleGmailRefreshIfRequiredSingleSendCliTests {

	@Test
	void usableCredentialSendsOnceWithoutRefresh() {
		FakeCredential credential = new FakeCredential(GoogleGmailRefreshIfRequiredSingleSendCli.Readiness.READY_WITHOUT_REFRESH,
				true, "opaque-token");
		AtomicInteger sends = new AtomicInteger();
		var outcome = execute(credential, (request, token) -> {
			sends.incrementAndGet();
			return new GoogleGmailRefreshIfRequiredSingleSendCli.SendResult(true, true, 200,
					"ACCEPTED", 1, 0, false);
		});

		assertThat(outcome.providerAccepted()).isTrue();
		assertThat(outcome.refreshRequests()).isZero();
		assertThat(outcome.sendRequests()).isOne();
		assertThat(sends).hasValue(1);
	}

	@Test
	void refreshRequiredUsesExactlyOneRefreshThenSendsOnceOnSameCredential() {
		FakeCredential credential = new FakeCredential(
				GoogleGmailRefreshIfRequiredSingleSendCli.Readiness.REFRESH_REQUIRED_AND_AVAILABLE, true, "new-token");
		var outcome = execute(credential, acceptedSender());

		assertThat(credential.refreshCalls).isOne();
		assertThat(credential.assessCalls).isEqualTo(2);
		assertThat(outcome.refreshAttempted()).isTrue();
		assertThat(outcome.refreshAccepted()).isTrue();
		assertThat(outcome.postRefreshUsable()).isTrue();
		assertThat(outcome.sendRequests()).isOne();
	}

	@Test
	void refreshFailureStopsBeforeAnySend() {
		FakeCredential credential = new FakeCredential(
				GoogleGmailRefreshIfRequiredSingleSendCli.Readiness.REFRESH_REQUIRED_AND_AVAILABLE, false, "opaque-token");
		AtomicInteger sends = new AtomicInteger();
		var outcome = execute(credential, (request, token) -> {
			sends.incrementAndGet();
			return GoogleGmailRefreshIfRequiredSingleSendCli.SendResult.rejected(1, "UNEXPECTED_SEND");
		});

		assertThat(outcome.status()).isEqualTo("REFRESH_FAILED");
		assertThat(outcome.sendRequests()).isZero();
		assertThat(sends).hasValue(0);
	}

	@Test
	void unusableCredentialAfterRefreshStopsBeforeAnySend() {
		FakeCredential credential = new FakeCredential(
				GoogleGmailRefreshIfRequiredSingleSendCli.Readiness.REFRESH_REQUIRED_AND_AVAILABLE, true, "opaque-token");
		credential.afterRefresh = GoogleGmailRefreshIfRequiredSingleSendCli.Readiness.REFRESH_REQUIRED_BUT_UNAVAILABLE;
		var outcome = execute(credential, acceptedSender());

		assertThat(outcome.status()).isEqualTo("POST_REFRESH_CREDENTIAL_UNUSABLE");
		assertThat(outcome.postRefreshUsable()).isFalse();
		assertThat(outcome.sendRequests()).isZero();
	}

	@Test
	void sendFailureDoesNotRetryOrFallback() {
		AtomicInteger sends = new AtomicInteger();
		var outcome = execute(new FakeCredential(
				GoogleGmailRefreshIfRequiredSingleSendCli.Readiness.READY_WITHOUT_REFRESH, true, "opaque-token"),
				(request, token) -> {
					sends.incrementAndGet();
					return GoogleGmailRefreshIfRequiredSingleSendCli.SendResult.rejected(1, "AUTHORIZATION_REJECTED");
				});

		assertThat(outcome.status()).isEqualTo("PROVIDER_REJECTED");
		assertThat(outcome.sendRequests()).isOne();
		assertThat(outcome.retries()).isZero();
		assertThat(outcome.fallbacks()).isZero();
		assertThat(sends).hasValue(1);
	}

	@Test
	void secondRefreshAttemptIsRejected() {
		FakeCredential credential = new FakeCredential(
				GoogleGmailRefreshIfRequiredSingleSendCli.Readiness.REFRESH_REQUIRED_AND_AVAILABLE, true, "opaque-token");
		var execution = new GoogleGmailRefreshIfRequiredSingleSendCli.BoundedExecution(credential, acceptedSender());

		execution.refreshOnce();
		assertThatThrownBy(execution::refreshOnce).isInstanceOf(IllegalStateException.class)
				.hasMessage("SECOND_REFRESH_ATTEMPT");
	}

	@Test
	void secondSendAttemptIsRejected() {
		FakeCredential credential = new FakeCredential(
				GoogleGmailRefreshIfRequiredSingleSendCli.Readiness.READY_WITHOUT_REFRESH, true, "opaque-token");
		var execution = new GoogleGmailRefreshIfRequiredSingleSendCli.BoundedExecution(credential, acceptedSender());

		execution.sendOnce(request(), "opaque-token");
		assertThatThrownBy(() -> execution.sendOnce(request(), "opaque-token"))
				.isInstanceOf(IllegalStateException.class).hasMessage("SECOND_SEND_ATTEMPT");
	}

	@Test
	void requestFactoryAllowsOnlyOneToRecipientAndNoExtraMessageOperations() throws Exception {
		NotificationGmailProperties properties = new NotificationGmailProperties(true, "global", "client", "tokens",
				"default", "sender@example.invalid", "recipient@example.invalid");
		var message = new GoogleGmailRequestFactory().create(request(), properties);
		byte[] raw = Base64.getUrlDecoder().decode(message.getRaw());
		MimeMessage mime = new MimeMessage(Session.getInstance(new java.util.Properties()), new ByteArrayInputStream(raw));

		assertThat(mime.getRecipients(jakarta.mail.Message.RecipientType.TO)).hasSize(1);
		assertThat(mime.getRecipients(jakarta.mail.Message.RecipientType.CC)).isNull();
		assertThat(mime.getRecipients(jakarta.mail.Message.RecipientType.BCC)).isNull();
		assertThat(mime.getContent().toString()).doesNotContain("attachment");
	}

	@Test
	void sanitizedOutcomeExcludesTokensAddressesAndRawProviderData() {
		var outcome = execute(new FakeCredential(
				GoogleGmailRefreshIfRequiredSingleSendCli.Readiness.READY_WITHOUT_REFRESH, true,
				"opaque-access-token-secret"), acceptedSender());
		String rendered = outcome.toString();

		assertThat(rendered).doesNotContain("opaque-access-token-secret", "sender@example.invalid",
				"recipient@example.invalid", "raw-provider-response");
		assertThat(outcome.messageIdPresent()).isTrue();
	}

	@Test
	void contractDigestIsBoundToIndependentRefreshIfRequiredContract() {
		assertThat(GoogleGmailRefreshIfRequiredSingleSendCli.CONTRACT_DIGEST)
				.isEqualTo("35702d6d6698b78f08757b2560deb2bfee50503d0b8cc90b8fd2fcdf9431535f");
	}

	private static GoogleGmailRefreshIfRequiredSingleSendCli.SendPort acceptedSender() {
		return (request, token) -> new GoogleGmailRefreshIfRequiredSingleSendCli.SendResult(true, true, 200,
				"ACCEPTED", 1, 0, false);
	}

	private static GoogleGmailRefreshIfRequiredSingleSendCli.Outcome execute(
			FakeCredential credential, GoogleGmailRefreshIfRequiredSingleSendCli.SendPort sender) {
		return GoogleGmailRefreshIfRequiredSingleSendCli.executeOffline(credential, sender, request());
	}

	private static NotificationRequest request() {
		return new NotificationRequest(UUID.fromString("11111111-1111-4111-8111-111111111111"),
				new TenantId(UUID.fromString("22222222-2222-4222-8222-222222222222")),
				UUID.fromString("33333333-3333-4333-8333-333333333333"), "r4-422-test", NotificationChannel.EMAIL,
				new NotificationRecipient("recipient@example.invalid"), new NotificationSender("sender@example.invalid"),
				"r4-422-test", "Subject", "Body", 1,
				UUID.fromString("44444444-4444-4444-8444-444444444444"), Instant.parse("2026-08-30T00:00:00Z"),
				Map.of("privacy_boundary", "synthetic-only"));
	}

	private static final class FakeCredential implements GoogleGmailRefreshIfRequiredSingleSendCli.CredentialPort {
		private GoogleGmailRefreshIfRequiredSingleSendCli.Readiness readiness;
		private GoogleGmailRefreshIfRequiredSingleSendCli.Readiness afterRefresh;
		private final boolean refreshAccepted;
		private final String token;
		private int refreshCalls;
		private int assessCalls;

		private FakeCredential(GoogleGmailRefreshIfRequiredSingleSendCli.Readiness readiness,
				boolean refreshAccepted, String token) {
			this.readiness = readiness;
			this.refreshAccepted = refreshAccepted;
			this.token = token;
		}

		@Override
		public GoogleGmailRefreshIfRequiredSingleSendCli.Readiness assess() {
			assessCalls++;
			return readiness;
		}

		@Override
		public GoogleGmailRefreshIfRequiredSingleSendCli.RefreshResult refreshOnce() {
			refreshCalls++;
			if (refreshAccepted) readiness = afterRefresh == null
					? GoogleGmailRefreshIfRequiredSingleSendCli.Readiness.READY_WITHOUT_REFRESH : afterRefresh;
			return new GoogleGmailRefreshIfRequiredSingleSendCli.RefreshResult(refreshAccepted,
					refreshAccepted ? "REFRESH_ACCEPTED" : "REFRESH_REQUEST_FAILED");
		}

		@Override
		public String authorizationToken() {
			return token;
		}
	}
}
