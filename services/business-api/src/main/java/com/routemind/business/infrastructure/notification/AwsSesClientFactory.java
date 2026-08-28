package com.routemind.business.infrastructure.notification;

import java.util.Objects;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.ses.SesClient;

/** Creates a non-sending SES client; no bean invokes this factory by default. */
public final class AwsSesClientFactory {

	private final AwsSesCredentialProviderFactory credentials;

	public AwsSesClientFactory(AwsSesCredentialProviderFactory credentials) {
		this.credentials = Objects.requireNonNull(credentials, "credentials");
	}

	public SesClient create(NotificationSesProperties properties) {
		Objects.requireNonNull(properties, "properties");
		if (!properties.enabled()) {
			throw new IllegalStateException("AWS SES adapter is disabled");
		}
		return SesClient.builder()
				.region(Region.of(properties.region()))
				.credentialsProvider(credentials.create(properties))
				.build();
	}
}
