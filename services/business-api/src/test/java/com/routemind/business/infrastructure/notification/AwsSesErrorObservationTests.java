package com.routemind.business.infrastructure.notification;

import static org.assertj.core.api.Assertions.assertThat;

import com.routemind.business.application.notification.NotificationChannel;
import com.routemind.business.application.notification.NotificationRecipient;
import com.routemind.business.application.notification.NotificationRequest;
import com.routemind.business.application.notification.NotificationResult;
import com.routemind.business.application.notification.NotificationSender;
import com.routemind.business.application.notification.NotificationStatus;
import com.routemind.business.domain.security.TenantId;
import java.lang.reflect.Proxy;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;
import software.amazon.awssdk.awscore.exception.AwsErrorDetails;
import software.amazon.awssdk.http.SdkHttpResponse;
import software.amazon.awssdk.services.ses.SesClient;
import software.amazon.awssdk.services.ses.model.SesException;

class AwsSesErrorObservationTests {

	private static final String SENDER = "synthetic-sender@example.invalid";
	private static final String RECIPIENT = "synthetic-recipient@example.invalid";

	@Test
	void capturesStructuredAccessDeniedWithoutRawExceptionLeakage() {
		String accountId = "123456" + "789012";
		String arn = "arn:aws:ses:ap-northeast-1:" + accountId + ":identity/" + SENDER;
		String accessKey = "AKIA" + "ABCDEFGHIJKLMNOP";
		String secret = "synthetic-secret-and-session-token-material";
		String requestId = "synthetic-provider-request-identifier";
		String unsafeMessage = "Denied " + arn + " for " + RECIPIENT + " using " + accessKey + " " + secret;
		SesException exception = accessDenied(unsafeMessage, requestId);
		SesRequestShapeAudit shape = SesRequestShapeAudit.inspect(new AwsSesRequestFactory()
				.create(request(), properties()));

		AwsSesErrorObservation observation = AwsSesErrorObservation.from(exception, "ap-northeast-1", shape,
				Instant.parse("2026-08-29T00:00:00Z"));

		assertThat(observation.serviceErrorCode()).isEqualTo("AccessDenied");
		assertThat(observation.httpStatus()).isEqualTo(403);
		assertThat(observation.requestId()).isEqualTo(AwsSesErrorObservation.RequestIdHandling.PRESENT_REDACTED);
		assertThat(observation.normalizedCategory())
				.isEqualTo(AwsSesErrorObservation.Category.AUTHORIZATION_REJECTED);
		assertThat(observation.sanitizedProviderSemantic()).isEqualTo("AUTHORIZATION_REJECTED");
		assertThat(observation.providerAcceptance()).isFalse();
		assertThat(observation.requestCount()).isEqualTo(1);
		assertThat(observation.retryCount()).isZero();
		assertThat(observation.fallbackUsed()).isFalse();
		assertThat(observation.toString()).doesNotContain(unsafeMessage, arn, accountId, SENDER, RECIPIENT,
				accessKey, secret, requestId);
	}

	@Test
	void providerRecordsOneSanitizedFailureAndDoesNotRetry() {
		AtomicInteger calls = new AtomicInteger();
		SesException exception = accessDenied("unsafe provider detail " + RECIPIENT,
				"synthetic-provider-request-identifier");
		SesClient client = throwingClient(calls, exception);
		AtomicReference<AwsSesErrorObservation> captured = new AtomicReference<>();
		AwsSesNotificationProvider provider = new AwsSesNotificationProvider(client, properties(),
				new AwsSesRequestFactory(), captured::set);

		NotificationResult result = provider.send(request());

		assertThat(calls).hasValue(1);
		assertThat(result.status()).isEqualTo(NotificationStatus.DEAD_LETTER);
		assertThat(result.failureClass()).isEqualTo("AUTHORIZATION_REJECTED");
		assertThat(result.provenance().authenticatedReceipt()).isFalse();
		assertThat(captured.get()).isNotNull();
		assertThat(captured.get().providerAcceptance()).isFalse();
		assertThat(captured.get().retryCount()).isZero();
	}

	@Test
	void unknownOrUnsafeServiceErrorCodeIsNotPersisted() {
		AwsErrorDetails details = AwsErrorDetails.builder()
				.errorCode("unsafe code with spaces " + SENDER)
				.errorMessage("raw message " + RECIPIENT)
				.sdkHttpResponse(SdkHttpResponse.builder().statusCode(400).build())
				.serviceName("ses")
				.build();
		SesException.Builder builder = SesException.builder();
		builder.message("raw " + SENDER);
		builder.awsErrorDetails(details);
		builder.statusCode(400);
		SesException exception = (SesException) builder.build();
		AwsSesErrorObservation observation = AwsSesErrorObservation.from(exception, "ap-northeast-1",
				SesRequestShapeAudit.inspect(new AwsSesRequestFactory().create(request(), properties())), Instant.now());

		assertThat(observation.serviceErrorCode()).isEqualTo("UNAVAILABLE_OR_UNSAFE");
		assertThat(observation.toString()).doesNotContain(SENDER, RECIPIENT, "unsafe code", "raw message");
	}

	private static SesException accessDenied(String message, String requestId) {
		AwsErrorDetails details = AwsErrorDetails.builder()
				.errorCode("AccessDenied")
				.errorMessage(message)
				.sdkHttpResponse(SdkHttpResponse.builder().statusCode(403).build())
				.serviceName("ses")
				.build();
		SesException.Builder builder = SesException.builder();
		builder.message(message);
		builder.awsErrorDetails(details);
		builder.statusCode(403);
		builder.requestId(requestId);
		return (SesException) builder.build();
	}

	private static SesClient throwingClient(AtomicInteger calls, SesException exception) {
		return (SesClient) Proxy.newProxyInstance(SesClient.class.getClassLoader(), new Class<?>[] { SesClient.class },
				(proxy, method, args) -> {
					if (method.getName().equals("sendEmail")) {
						calls.incrementAndGet();
						throw exception;
					}
					if (method.getName().equals("serviceName")) return "ses";
					if (method.getName().equals("close")) return null;
					if (method.getName().equals("toString")) return "SyntheticSesClient";
					throw new UnsupportedOperationException(method.getName());
				});
	}

	private static NotificationSesProperties properties() {
		return new NotificationSesProperties(true, "routemind-ses", "ap-northeast-1", SENDER, RECIPIENT);
	}

	private static NotificationRequest request() {
		return new NotificationRequest(
				UUID.fromString("11111111-1111-4111-8111-111111111111"),
				new TenantId(UUID.fromString("22222222-2222-4222-8222-222222222222")),
				UUID.fromString("33333333-3333-4333-8333-333333333333"),
				"r4-422-error-observation", NotificationChannel.EMAIL,
				new NotificationRecipient(RECIPIENT), new NotificationSender(SENDER),
				"r4-422-synthetic", "Synthetic subject", "Synthetic body", 1,
				UUID.fromString("44444444-4444-4444-8444-444444444444"),
				Instant.parse("2026-08-29T00:00:00Z"), Map.of("privacy_boundary", "synthetic-only"));
	}
}
