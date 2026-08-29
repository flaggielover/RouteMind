package com.routemind.business.infrastructure.notification;

import com.google.api.client.googleapis.javanet.GoogleNetHttpTransport;
import com.google.api.client.json.jackson2.JacksonFactory;
import com.google.api.services.gmail.Gmail;
import com.google.api.client.http.HttpRequestInitializer;
import java.io.IOException;
import java.security.GeneralSecurityException;
import java.util.Objects;

/** Builds a Gmail client only after an explicit OAuth initializer is supplied. */
public final class GoogleGmailClientFactory {

	public Gmail create(NotificationGmailProperties properties, HttpRequestInitializer initializer) {
		Objects.requireNonNull(properties, "properties");
		Objects.requireNonNull(initializer, "initializer");
		if (!properties.enabled()) throw new IllegalStateException("Gmail adapter is disabled");
		try {
			return new Gmail.Builder(GoogleNetHttpTransport.newTrustedTransport(),
					JacksonFactory.getDefaultInstance(), initializer)
					.setApplicationName("RouteMind")
					.build();
		}
		catch (GeneralSecurityException | IOException exception) {
			throw new IllegalStateException("unable to initialize Google HTTPS transport", exception);
		}
	}
}
