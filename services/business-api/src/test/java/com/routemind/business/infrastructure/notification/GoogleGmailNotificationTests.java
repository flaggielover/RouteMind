package com.routemind.business.infrastructure.notification;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;
import static org.assertj.core.api.Assertions.assertThatIllegalStateException;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.google.api.services.gmail.model.Message;
import com.google.api.services.gmail.Gmail;
import com.routemind.business.application.notification.NotificationChannel;
import com.routemind.business.application.notification.NotificationRecipient;
import com.routemind.business.application.notification.NotificationRequest;
import com.routemind.business.application.notification.NotificationSender;
import com.routemind.business.application.notification.NotificationStatus;
import com.routemind.business.domain.security.TenantId;
import jakarta.mail.Session;
import jakarta.mail.internet.MimeMessage;
import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;
import java.util.Map;
import java.util.Properties;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class GoogleGmailNotificationTests {

	private static final String SENDER = "synthetic-sender@example.invalid";
	private static final String RECIPIENT = "synthetic-recipient@example.invalid";

	@Test
	void gmailIsDisabledByDefaultAndReadinessNeverReadsOAuthValues() {
		NotificationGmailProperties properties = new NotificationGmailProperties(false, "global", "", "", "",
				SENDER, RECIPIENT);

		assertThat(properties.toString()).contains("enabled=false", "senderConfigured=true")
				.doesNotContain(SENDER, RECIPIENT);
		assertThat(GoogleGmailAuthenticationReadiness.assess(properties))
				.isEqualTo(GoogleGmailAuthenticationReadiness.Status.MISSING);
	}

	@Test
	void enabledGmailRequiresExternalOAuthConfiguration() {
		assertThatIllegalArgumentException().isThrownBy(() -> new NotificationGmailProperties(true, "global", "", "",
				"default", SENDER, RECIPIENT));
		assertThatIllegalArgumentException().isThrownBy(() -> new NotificationGmailProperties(true, "global", "client",
				"tokens", "default", "", RECIPIENT));
	}

	@Test
	void requestFactoryProducesOneUrlSafeUtf8MimeMessageWithoutExtraRecipients() throws Exception {
		NotificationGmailProperties properties = properties();
		Message message = new GoogleGmailRequestFactory().create(request("主题", "東京の本文"), properties);

		assertThat(message.getRaw()).isNotBlank().doesNotContain("+", "/");
		byte[] decoded = Base64.getUrlDecoder().decode(message.getRaw());
		MimeMessage mime = new MimeMessage(Session.getInstance(new Properties()), new ByteArrayInputStream(decoded));
		assertThat(mime.getFrom()).hasSize(1);
		assertThat(mime.getRecipients(jakarta.mail.Message.RecipientType.TO)).hasSize(1);
		assertThat(mime.getRecipients(jakarta.mail.Message.RecipientType.CC)).isNull();
		assertThat(mime.getRecipients(jakarta.mail.Message.RecipientType.BCC)).isNull();
		assertThat(mime.getSubject()).isEqualTo("主题");
		assertThat(mime.getContent().toString()).contains("東京の本文");
	}

	@Test
	void requestFactoryFailsClosedForMismatchedEndpointsOrDisabledAdapter() {
		GoogleGmailRequestFactory factory = new GoogleGmailRequestFactory();
		assertThatIllegalArgumentException().isThrownBy(() -> factory.create(request(SENDER, RECIPIENT),
				new NotificationGmailProperties(true, "global", "client", "tokens", "default", SENDER,
						"other@example.invalid")));
		assertThatIllegalStateException().isThrownBy(() -> factory.create(request(SENDER, RECIPIENT),
				new NotificationGmailProperties(false, "global", "", "", "", SENDER, RECIPIENT)));
	}

	@Test
	void providerStatusesAreNormalizedWithoutRetainingGooglePayloads() {
		assertThat(GoogleGmailErrorObservation.fromStatus(401, "invalid_grant", "global", Instant.now()).category())
				.isEqualTo(GoogleGmailErrorObservation.Category.AUTHENTICATION_REJECTED);
		assertThat(GoogleGmailErrorObservation.fromStatus(403, "forbidden", "global", Instant.now()).category())
				.isEqualTo(GoogleGmailErrorObservation.Category.AUTHORIZATION_REJECTED);
		assertThat(GoogleGmailErrorObservation.fromStatus(429, "rateLimitExceeded", "global", Instant.now()).safeReason())
				.isEqualTo("RATELIMITEXCEEDED");
		assertThat(GoogleGmailErrorObservation.fromStatus(503, "backendError", "global", Instant.now()).category())
				.isEqualTo(GoogleGmailErrorObservation.Category.PROVIDER_SERVER_FAILURE);
		assertThat(GoogleGmailErrorObservation.fromStatus(400, "bad request with secret", "global", Instant.now())
				.safeReason()).isEqualTo("BAD_REQUEST_WITH_SECRET");
	}

	@Test
	void acceptedObservationCarriesOnlyMessageIdPresence() {
		GoogleGmailErrorObservation observation = GoogleGmailErrorObservation.accepted("global", true, Instant.now());
		assertThat(observation.category()).isEqualTo(GoogleGmailErrorObservation.Category.ACCEPTED);
		assertThat(observation.messageIdPresent()).isTrue();
		assertThat(observation.toString()).doesNotContain("message-id-value");
	}

	@Test
	void providerUsesExactlyOneMockedSendWithoutRetryOrFallback() throws Exception {
		Gmail client = mock(Gmail.class);
		Gmail.Users users = mock(Gmail.Users.class);
		Gmail.Users.Messages messages = mock(Gmail.Users.Messages.class);
		Gmail.Users.Messages.Send send = mock(Gmail.Users.Messages.Send.class);
		when(client.users()).thenReturn(users);
		when(users.messages()).thenReturn(messages);
		when(messages.send(eq("me"), any(Message.class))).thenReturn(send);
		when(send.execute()).thenReturn(new Message().setId("synthetic-message-id"));
		GoogleGmailObservationSink sink = mock(GoogleGmailObservationSink.class);

		GoogleGmailNotificationProvider provider = new GoogleGmailNotificationProvider(client, properties(),
				new GoogleGmailRequestFactory(), sink);
		var result = provider.send(request("主题", "東京の本文"));

		assertThat(result.status()).isEqualTo(NotificationStatus.ACCEPTED);
		verify(messages).send(eq("me"), any(Message.class));
		verify(send).execute();
	}

	private static NotificationGmailProperties properties() {
		return new NotificationGmailProperties(true, "global", "external/client-secrets.json", "external/tokens",
				"operator", SENDER, RECIPIENT);
	}

	private static NotificationRequest request(String subject, String body) {
		return new NotificationRequest(UUID.fromString("11111111-1111-4111-8111-111111111111"),
				new TenantId(UUID.fromString("22222222-2222-4222-8222-222222222222")),
				UUID.fromString("33333333-3333-4333-8333-333333333333"), "gmail-offline-test",
				NotificationChannel.EMAIL, new NotificationRecipient(RECIPIENT), new NotificationSender(SENDER),
				"r4-422-gmail-synthetic", subject, body, 1,
				UUID.fromString("44444444-4444-4444-8444-444444444444"), Instant.parse("2026-08-29T00:00:00Z"),
				Map.of("privacy_boundary", "synthetic-only"));
	}
}
