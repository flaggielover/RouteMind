package com.routemind.business.infrastructure.notification;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;
import static org.assertj.core.api.Assertions.assertThatIllegalStateException;

import org.junit.jupiter.api.Test;
import software.amazon.awssdk.services.ses.SesClient;

class NotificationSesConfigurationTests {

	@Test
	void disabledConfigurationIsSafeAndDoesNotExposeEndpointValues() {
		NotificationSesProperties properties = new NotificationSesProperties(false, "", "ap-northeast-1",
				"synthetic-sender@example.invalid", "synthetic-recipient@example.invalid");

		assertThat(properties.toString()).contains("enabled=false", "profileConfigured=false", "senderConfigured=true")
				.doesNotContain("synthetic-sender@example.invalid", "synthetic-recipient@example.invalid");
		assertThat(AwsSesAuthenticationReadiness.assess(properties, "routemind-ses"))
				.isEqualTo(AwsSesAuthenticationReadiness.Status.MISSING);
	}

	@Test
	void enabledConfigurationRequiresValidNonSecretEndpoints() {
		assertThatIllegalArgumentException().isThrownBy(() -> new NotificationSesProperties(true, "routemind-ses",
				"ap-northeast-1", "", "synthetic-recipient@example.invalid"));
		assertThatIllegalArgumentException().isThrownBy(() -> new NotificationSesProperties(true, "bad profile",
				"ap-northeast-1", "sender@example.invalid", "recipient@example.invalid"));
		assertThatIllegalArgumentException().isThrownBy(() -> new NotificationSesProperties(false, "", "not a region",
				"", ""));
	}

	@Test
	void readinessUsesOnlyProfileConfigurationAndNeverResolvesCredentials() {
		NotificationSesProperties properties = new NotificationSesProperties(true, "", "ap-northeast-1",
				"sender@example.invalid", "recipient@example.invalid");

		assertThat(AwsSesAuthenticationReadiness.assess(properties, "routemind-ses"))
				.isEqualTo(AwsSesAuthenticationReadiness.Status.AVAILABLE);
		assertThat(AwsSesAuthenticationReadiness.assess(properties, ""))
				.isEqualTo(AwsSesAuthenticationReadiness.Status.MISSING);
		assertThat(AwsSesAuthenticationReadiness.assess(properties, "bad profile"))
				.isEqualTo(AwsSesAuthenticationReadiness.Status.INVALID_CONFIGURATION);
	}

	@Test
	void sdkFactoryUsesStandardProfileChainWithoutSending() {
		NotificationSesProperties disabled = new NotificationSesProperties(false, "routemind-ses", "ap-northeast-1",
				"sender@example.invalid", "recipient@example.invalid");
		AwsSesClientFactory factory = new AwsSesClientFactory(new AwsSesCredentialProviderFactory());
		assertThatIllegalStateException().isThrownBy(() -> factory.create(disabled));

		NotificationSesProperties enabled = new NotificationSesProperties(true, "routemind-ses", "ap-northeast-1",
				"sender@example.invalid", "recipient@example.invalid");
		try (SesClient client = factory.create(enabled)) {
			assertThat(client.serviceName()).isEqualTo("ses");
		}
	}
}
