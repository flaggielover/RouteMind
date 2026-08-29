package com.routemind.business.infrastructure.notification;

import com.google.api.client.googleapis.json.GoogleJsonResponseException;
import com.google.api.services.gmail.Gmail;
import com.google.api.services.gmail.model.Message;
import com.routemind.business.application.notification.NotificationProvider;
import com.routemind.business.application.notification.NotificationRequest;
import com.routemind.business.application.notification.NotificationResult;
import java.io.IOException;
import java.net.SocketTimeoutException;
import java.time.Instant;
import java.util.Objects;

/** Explicitly injected Gmail adapter. Construction never performs a network request. */
public final class GoogleGmailNotificationProvider implements NotificationProvider {

	private static final String PROVIDER = "GOOGLE_GMAIL_API";
	private static final String OPERATION = "users.messages.send";

	private final Gmail client;
	private final NotificationGmailProperties properties;
	private final GoogleGmailRequestFactory requestFactory;
	private final GoogleGmailObservationSink observationSink;

	public GoogleGmailNotificationProvider(Gmail client, NotificationGmailProperties properties,
			GoogleGmailRequestFactory requestFactory, GoogleGmailObservationSink observationSink) {
		this.client = Objects.requireNonNull(client, "client");
		this.properties = Objects.requireNonNull(properties, "properties");
		this.requestFactory = Objects.requireNonNull(requestFactory, "requestFactory");
		this.observationSink = Objects.requireNonNull(observationSink, "observationSink");
		if (!properties.enabled()) throw new IllegalStateException("Gmail adapter is disabled");
	}

	@Override
	public NotificationResult send(NotificationRequest request) {
		Message outbound = requestFactory.create(request, properties);
		try {
			Message response = client.users().messages().send("me", outbound).execute();
			observationSink.record(GoogleGmailErrorObservation.accepted(properties.region(),
					response != null && response.getId() != null && !response.getId().isBlank(), Instant.now()));
			return NotificationResult.accepted(request, PROVIDER, properties.region(), OPERATION);
		}
		catch (GoogleJsonResponseException exception) {
			int status = exception.getStatusCode();
			String reason = exception.getDetails() == null || exception.getDetails().getErrors() == null
					|| exception.getDetails().getErrors().isEmpty() ? null
					: exception.getDetails().getErrors().get(0).getReason();
			GoogleGmailErrorObservation observation = GoogleGmailErrorObservation.fromStatus(status, reason,
					properties.region(), Instant.now());
			observationSink.record(observation);
			return failureResult(request, observation);
		}
		catch (IOException exception) {
			GoogleGmailErrorObservation.Category category = exception instanceof SocketTimeoutException
					? GoogleGmailErrorObservation.Category.TIMEOUT
					: GoogleGmailErrorObservation.Category.PROVIDER_UNAVAILABLE;
			GoogleGmailErrorObservation observation = GoogleGmailErrorObservation.clientFailure(category,
					properties.region(), Instant.now());
			observationSink.record(observation);
			return failureResult(request, observation);
		}
		catch (RuntimeException exception) {
			GoogleGmailErrorObservation observation = GoogleGmailErrorObservation.clientFailure(
					GoogleGmailErrorObservation.Category.UNKNOWN_PROVIDER_FAILURE, properties.region(), Instant.now());
			observationSink.record(observation);
			return failureResult(request, observation);
		}
	}

	private NotificationResult failureResult(NotificationRequest request, GoogleGmailErrorObservation observation) {
		return switch (observation.category()) {
			case ACCEPTED -> NotificationResult.accepted(request, PROVIDER, properties.region(), OPERATION);
			case RATE_LIMITED, PROVIDER_SERVER_FAILURE, PROVIDER_UNAVAILABLE, TIMEOUT ->
				NotificationResult.retryable(request, PROVIDER, properties.region(), observation.category().name(), OPERATION);
			case AUTHENTICATION_REJECTED, AUTHORIZATION_REJECTED, INVALID_REQUEST, UNKNOWN_PROVIDER_FAILURE ->
				NotificationResult.deadLetter(request, PROVIDER, properties.region(), observation.category().name(), OPERATION);
		};
	}
}
