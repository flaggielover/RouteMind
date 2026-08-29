package com.routemind.business.infrastructure.notification;

import com.google.api.client.auth.oauth2.Credential;
import com.google.api.client.googleapis.auth.oauth2.GoogleAuthorizationCodeFlow;
import com.google.api.client.googleapis.javanet.GoogleNetHttpTransport;
import com.google.api.client.util.store.FileDataStoreFactory;
import java.nio.file.Path;

/** Offline-only readiness command; it never invokes Credential.refreshToken or Gmail. */
public final class GmailCredentialRefreshReadinessCli {

	private GmailCredentialRefreshReadinessCli() { }

	public static void main(String[] args) throws Exception {
		if (args.length != 1 || !"--offline-readiness-only".equals(args[0])) {
			throw new IllegalArgumentException("explicit offline readiness mode is required");
		}
		Path repositoryRoot = Path.of(System.getenv().getOrDefault("ROUTEMIND_REPOSITORY_ROOT", "."));
		GmailOAuthBootstrapConfiguration configuration = GmailOAuthBootstrapConfiguration.fromEnvironment(System.getenv());
		GmailOAuthPathPolicy.ValidatedPaths paths = GmailOAuthPathPolicy.validate(repositoryRoot, configuration);
		GoogleAuthorizationCodeFlow flow = GoogleGmailOAuthBootstrap.buildFlow(
				GoogleNetHttpTransport.newTrustedTransport(),
				new FileDataStoreFactory(paths.tokenStoreDirectory().toFile()), configuration, repositoryRoot);
		Credential credential = GoogleGmailOAuthBootstrap.loadStoredCredential(flow,
				new NotificationGmailProperties(true, "global", paths.clientCredentialFile().toString(),
						paths.tokenStoreDirectory().toString(), configuration.oauthUserId(),
						"synthetic-sender@example.invalid", "synthetic-recipient@example.invalid"));
		GoogleGmailCredentialRefreshReadiness.Assessment assessment =
				GoogleGmailCredentialRefreshReadiness.assess(credential);
		System.out.println("TOKEN_STORE_PATH_REFERENCE=SET");
		System.out.println("TOKEN_STORE_REPOSITORY_EXTERNAL=true");
		System.out.println("TOKEN_STORE_EXISTS=true");
		System.out.println("STORED_CREDENTIAL_LOADING=AVAILABLE");
		System.out.println("REFRESH_REQUIRED=" + assessment.refreshRequired());
		System.out.println("REFRESH_CAPABILITY=" + (assessment.refreshCapabilityAvailable() ? "AVAILABLE" : "UNAVAILABLE"));
		System.out.println("READINESS_STATUS=" + assessment.status().name());
		System.out.println("TOKEN_REFRESH_REQUESTS=0");
		System.out.println("GMAIL_API_REQUESTS=0");
		System.out.println("OAUTH_SESSIONS=0");
		System.out.println("TOKEN_EXCHANGES=0");
	}
}
