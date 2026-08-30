package com.routemind.business.infrastructure.notification;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.google.api.client.http.HttpHeaders;
import com.google.api.client.http.HttpRequest;
import org.junit.jupiter.api.Test;

class GoogleGmailSingleSendV2CliTests {

	@Test
	void requestInitializerDisablesRetriesRedirectsAndHandlers() {
		HttpRequest request = mock(HttpRequest.class);
		HttpHeaders headers = new HttpHeaders();
		when(request.getHeaders()).thenReturn(headers);

		GoogleGmailSingleSendV2Cli.configureRequest(request, "opaque-test-access-token");

		verify(request).setNumberOfRetries(0);
		verify(request).setFollowRedirects(false);
		verify(request).setIOExceptionHandler(null);
		verify(request).setUnsuccessfulResponseHandler(null);
		verify(request).setConnectTimeout(10_000);
		verify(request).setReadTimeout(30_000);
		assertThat(headers.getAuthorization()).isEqualTo("Bearer opaque-test-access-token");
	}
}
