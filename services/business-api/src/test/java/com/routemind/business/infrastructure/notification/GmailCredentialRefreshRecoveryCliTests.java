package com.routemind.business.infrastructure.notification;

import static org.assertj.core.api.Assertions.assertThat;

import com.google.api.client.http.GenericUrl;
import com.google.api.client.http.HttpRequest;
import com.google.api.client.http.javanet.NetHttpTransport;
import org.junit.jupiter.api.Test;

class GmailCredentialRefreshRecoveryCliTests {

	@Test
	void refreshRequestInitializerDisablesRetriesAndRedirects() throws Exception {
		HttpRequest request = new NetHttpTransport().createRequestFactory()
				.buildGetRequest(new GenericUrl("https://oauth2.example.invalid/token"));

		GmailCredentialRefreshRecoveryCli.configureRefreshRequest(request);

		assertThat(request.getNumberOfRetries()).isZero();
		assertThat(request.getFollowRedirects()).isFalse();
		assertThat(request.getIOExceptionHandler()).isNull();
		assertThat(request.getUnsuccessfulResponseHandler()).isNull();
	}

	@Test
	void contractDigestIsBoundToTheApprovedRefreshContract() {
		assertThat(GmailCredentialRefreshRecoveryCli.CONTRACT_DIGEST)
				.isEqualTo("6c2b454101787c72459b3a5a7f01c18b25cf09d19ffd8ed90aaf3044e8b4b39f");
	}
}
