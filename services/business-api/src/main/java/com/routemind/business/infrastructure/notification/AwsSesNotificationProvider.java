package com.routemind.business.infrastructure.notification;

import com.routemind.business.application.notification.NotificationProvider;
import com.routemind.business.application.notification.NotificationRequest;
import com.routemind.business.application.notification.NotificationResult;
import java.time.Instant;
import java.util.Objects;
import software.amazon.awssdk.core.exception.SdkClientException;
import software.amazon.awssdk.services.ses.SesClient;
import software.amazon.awssdk.services.ses.model.SendEmailRequest;
import software.amazon.awssdk.services.ses.model.SesException;

/** Disabled-by-default SES provider boundary with structured, non-content failure observations. */
public final class AwsSesNotificationProvider implements NotificationProvider {

	private final SesClient client;
	private final NotificationSesProperties properties;
	private final AwsSesRequestFactory requestFactory;
	private final AwsSesErrorObservationSink errorSink;

	public AwsSesNotificationProvider(SesClient client, NotificationSesProperties properties,
			AwsSesRequestFactory requestFactory, AwsSesErrorObservationSink errorSink) {
		this.client = Objects.requireNonNull(client, "client");
		this.properties = Objects.requireNonNull(properties, "properties");
		this.requestFactory = Objects.requireNonNull(requestFactory, "requestFactory");
		this.errorSink = Objects.requireNonNull(errorSink, "errorSink");
		if (!properties.enabled()) throw new IllegalStateException("AWS SES adapter is disabled");
	}

	@Override
	public NotificationResult send(NotificationRequest request) {
		SendEmailRequest sdkRequest = requestFactory.create(request, properties);
		SesRequestShapeAudit shape = SesRequestShapeAudit.inspect(sdkRequest);
		try {
			client.sendEmail(sdkRequest);
			return NotificationResult.accepted(request, "AWS_SES", properties.region());
		}
		catch (SesException exception) {
			AwsSesErrorObservation observation = AwsSesErrorObservation.from(exception,
					properties.region(), shape, Instant.now());
			errorSink.record(observation);
			return terminalResult(request, observation);
		}
		catch (SdkClientException exception) {
			AwsSesErrorObservation observation = AwsSesErrorObservation.from(exception,
					properties.region(), shape, Instant.now());
			errorSink.record(observation);
			return NotificationResult.retryable(request, "AWS_SES", properties.region(),
					observation.normalizedCategory().name());
		}
	}

	private NotificationResult terminalResult(NotificationRequest request, AwsSesErrorObservation observation) {
		return switch (observation.normalizedCategory()) {
			case RATE_LIMITED, PROVIDER_SERVER_FAILURE -> NotificationResult.retryable(request, "AWS_SES",
					properties.region(), observation.normalizedCategory().name());
			case AUTHORIZATION_REJECTED, PROVIDER_REQUEST_REJECTED, CLIENT_RUNTIME_FAILURE ->
				NotificationResult.deadLetter(request, "AWS_SES", properties.region(),
						observation.normalizedCategory().name());
		};
	}
}
