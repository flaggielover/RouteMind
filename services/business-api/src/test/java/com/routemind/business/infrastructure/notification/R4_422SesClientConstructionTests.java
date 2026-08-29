package com.routemind.business.infrastructure.notification;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;

import org.junit.jupiter.api.Test;
import software.amazon.awssdk.auth.credentials.AwsCredentialsProvider;
import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider;
import software.amazon.awssdk.services.ses.SesClient;

class R4_422SesClientConstructionTests {

	@Test
	void constructsAndClosesSesClientWithMavenRuntimeClasspathWithoutSending() {
		NotificationSesProperties properties = new NotificationSesProperties(true, "routemind-ses",
				"ap-northeast-1", "synthetic-sender@example.invalid", "synthetic-recipient@example.invalid");
		AwsSesCredentialProviderFactory providerFactory = new AwsSesCredentialProviderFactory();
		AwsCredentialsProvider provider = providerFactory.create(properties);

		assertThat(provider).isInstanceOf(DefaultCredentialsProvider.class);
		assertThat(properties.region()).isEqualTo("ap-northeast-1");
		assertThatCode(() -> {
			try (SesClient client = new AwsSesClientFactory(providerFactory).create(properties)) {
				assertThat(client.serviceName()).isEqualTo("ses");
			}
		}).doesNotThrowAnyException();

		if (Boolean.getBoolean("routemind.ses.resolveCredentials")) {
			assertThatCode(() -> provider.resolveCredentials()).doesNotThrowAnyException();
		}
	}
}
