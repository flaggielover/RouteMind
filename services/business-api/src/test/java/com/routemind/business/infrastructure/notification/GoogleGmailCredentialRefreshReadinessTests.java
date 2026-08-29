package com.routemind.business.infrastructure.notification;

import static org.assertj.core.api.Assertions.assertThat;

import com.google.api.client.auth.oauth2.Credential;
import com.google.api.client.auth.oauth2.BearerToken;
import com.google.api.client.auth.oauth2.ClientParametersAuthentication;
import com.google.api.client.http.javanet.NetHttpTransport;
import com.google.api.client.json.jackson2.JacksonFactory;
import java.time.Instant;
import org.junit.jupiter.api.Test;

class GoogleGmailCredentialRefreshReadinessTests {

	@Test
	void expiredCredentialWithRefreshCapabilityIsReportedWithoutRefreshing() {
		Credential credential = credential("redacted-access", "redacted-refresh", Instant.now().minusSeconds(1));

		GoogleGmailCredentialRefreshReadiness.Assessment assessment =
				GoogleGmailCredentialRefreshReadiness.assess(credential);

		assertThat(assessment.status()).isEqualTo(
				GoogleGmailCredentialRefreshReadiness.Status.REFRESH_REQUIRED_AND_AVAILABLE);
		assertThat(assessment.refreshRequired()).isTrue();
		assertThat(assessment.refreshCapabilityAvailable()).isTrue();
		assertThat(assessment.toString()).doesNotContain("redacted-access", "redacted-refresh");
	}

	@Test
	void expiredCredentialWithoutRefreshCapabilityIsUnavailable() {
		Credential credential = credential("redacted-access", null, Instant.now().minusSeconds(1));

		assertThat(GoogleGmailCredentialRefreshReadiness.assess(credential).status())
				.isEqualTo(GoogleGmailCredentialRefreshReadiness.Status.REFRESH_REQUIRED_BUT_UNAVAILABLE);
	}

	@Test
	void usableCredentialDoesNotRequireRefresh() {
		Credential credential = credential("redacted-access", "redacted-refresh", Instant.now().plusSeconds(600));

		assertThat(GoogleGmailCredentialRefreshReadiness.assess(credential).status())
				.isEqualTo(GoogleGmailCredentialRefreshReadiness.Status.READY_WITHOUT_REFRESH);
	}

	@Test
	void nullCredentialIsMissing() {
		assertThat(GoogleGmailCredentialRefreshReadiness.assess(null).status())
				.isEqualTo(GoogleGmailCredentialRefreshReadiness.Status.MISSING);
	}

	private static Credential credential(String accessToken, String refreshToken, Instant expiresAt) {
		Credential credential = new Credential.Builder(BearerToken.authorizationHeaderAccessMethod())
				.setTransport(new NetHttpTransport())
				.setJsonFactory(JacksonFactory.getDefaultInstance())
				.setClientAuthentication(new ClientParametersAuthentication("test-client", "placeholder"))
				.setTokenServerEncodedUrl("https://oauth2.example.invalid/token")
				.build()
				.setAccessToken(accessToken)
				.setExpirationTimeMilliseconds(expiresAt.toEpochMilli());
		credential.setRefreshToken(refreshToken);
		return credential;
	}
}
