package com.routemind.business.infrastructure.notification;

import java.util.Objects;
import software.amazon.awssdk.auth.credentials.AwsCredentialsProvider;
import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider;

/**
 * Builds the AWS SDK v2 standard credential chain without resolving credentials.
 * The chain reads shared profiles only when a future, separately approved send occurs.
 */
public final class AwsSesCredentialProviderFactory {

	public AwsCredentialsProvider create(NotificationSesProperties properties) {
		Objects.requireNonNull(properties, "properties");
		String profile = properties.effectiveProfile(System.getenv("AWS_PROFILE"));
		if (profile.isBlank()) {
			return DefaultCredentialsProvider.builder().build();
		}
		return DefaultCredentialsProvider.builder().profileName(profile).build();
	}
}
