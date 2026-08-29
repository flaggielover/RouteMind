package com.routemind.business.infrastructure.notification;

import com.routemind.business.application.notification.NotificationChannel;
import com.routemind.business.application.notification.NotificationRequest;
import java.util.Objects;
import software.amazon.awssdk.services.ses.model.Body;
import software.amazon.awssdk.services.ses.model.Content;
import software.amazon.awssdk.services.ses.model.Destination;
import software.amazon.awssdk.services.ses.model.Message;
import software.amazon.awssdk.services.ses.model.SendEmailRequest;

/** Single production request-construction path for SES email delivery and offline audit. */
public final class AwsSesRequestFactory {

	public SendEmailRequest create(NotificationRequest request, NotificationSesProperties properties) {
		Objects.requireNonNull(request, "request");
		Objects.requireNonNull(properties, "properties");
		if (!properties.enabled()) {
			throw new IllegalStateException("AWS SES adapter is disabled");
		}
		if (request.channel() != NotificationChannel.EMAIL) {
			throw new IllegalArgumentException("AWS SES requires the EMAIL channel");
		}
		if (!request.sender().address().equals(properties.sender())) {
			throw new IllegalArgumentException("notification sender does not match bounded SES configuration");
		}
		if (!request.recipient().address().equals(properties.syntheticRecipient())) {
			throw new IllegalArgumentException("notification recipient does not match bounded SES configuration");
		}

		return SendEmailRequest.builder()
				.source(request.sender().address())
				.destination(Destination.builder().toAddresses(request.recipient().address()).build())
				.message(Message.builder()
						.subject(Content.builder().data(request.subject()).build())
						.body(Body.builder().text(Content.builder().data(request.body()).build()).build())
						.build())
				.build();
	}
}
