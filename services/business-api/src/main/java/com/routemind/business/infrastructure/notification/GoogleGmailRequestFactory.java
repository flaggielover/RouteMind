package com.routemind.business.infrastructure.notification;

import com.google.api.services.gmail.model.Message;
import com.routemind.business.application.notification.NotificationChannel;
import com.routemind.business.application.notification.NotificationRequest;
import jakarta.mail.Session;
import jakarta.mail.internet.InternetAddress;
import jakarta.mail.internet.MimeMessage;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.Objects;
import java.util.Properties;

/** Builds the provider-neutral notification as a URL-safe base64 RFC 2822 message. */
public final class GoogleGmailRequestFactory {

	public Message create(NotificationRequest request, NotificationGmailProperties properties) {
		Objects.requireNonNull(request, "request");
		Objects.requireNonNull(properties, "properties");
		if (!properties.enabled()) throw new IllegalStateException("Gmail adapter is disabled");
		if (request.channel() != NotificationChannel.EMAIL) {
			throw new IllegalArgumentException("Gmail requires the EMAIL channel");
		}
		if (!request.sender().address().equals(properties.sender())) {
			throw new IllegalArgumentException("notification sender does not match bounded Gmail configuration");
		}
		if (!request.recipient().address().equals(properties.syntheticRecipient())) {
			throw new IllegalArgumentException("notification recipient does not match bounded Gmail configuration");
		}

		try {
			MimeMessage mime = new MimeMessage(Session.getInstance(new Properties()));
			mime.setFrom(new InternetAddress(request.sender().address()));
			mime.setRecipients(jakarta.mail.Message.RecipientType.TO,
					new InternetAddress[] { new InternetAddress(request.recipient().address()) });
			mime.setSubject(request.subject(), StandardCharsets.UTF_8.name());
			mime.setText(request.body(), StandardCharsets.UTF_8.name());
			mime.saveChanges();
			ByteArrayOutputStream bytes = new ByteArrayOutputStream();
			mime.writeTo(bytes);
			return new Message().setRaw(Base64.getUrlEncoder().withoutPadding()
					.encodeToString(bytes.toByteArray()));
		}
		catch (Exception exception) {
			throw new IllegalArgumentException("unable to construct bounded Gmail message", exception);
		}
	}
}
