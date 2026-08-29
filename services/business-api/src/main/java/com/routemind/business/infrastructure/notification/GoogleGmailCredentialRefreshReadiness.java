package com.routemind.business.infrastructure.notification;

import com.google.api.client.auth.oauth2.Credential;
import java.util.Objects;

/** Read-only credential metadata assessment; it never refreshes or sends a request. */
public final class GoogleGmailCredentialRefreshReadiness {

	private static final long MINIMUM_USABLE_SECONDS = 120L;

	public enum Status {
		REFRESH_REQUIRED_AND_AVAILABLE,
		READY_WITHOUT_REFRESH,
		REFRESH_REQUIRED_BUT_UNAVAILABLE,
		MISSING
	}

	private GoogleGmailCredentialRefreshReadiness() { }

	public static Assessment assess(Credential credential) {
		if (credential == null) return new Assessment(Status.MISSING, false, false);
		boolean refreshRequired = credential.getAccessToken() == null
				|| credential.getAccessToken().isBlank()
				|| credential.getExpiresInSeconds() == null
				|| credential.getExpiresInSeconds() <= MINIMUM_USABLE_SECONDS;
		if (!refreshRequired) return new Assessment(Status.READY_WITHOUT_REFRESH, false, false);
		boolean refreshAvailable = credential.getRefreshToken() != null
				&& !credential.getRefreshToken().isBlank();
		return new Assessment(refreshAvailable ? Status.REFRESH_REQUIRED_AND_AVAILABLE
				: Status.REFRESH_REQUIRED_BUT_UNAVAILABLE, true, refreshAvailable);
	}

	public record Assessment(Status status, boolean refreshRequired, boolean refreshCapabilityAvailable) {
		public Assessment {
			Objects.requireNonNull(status, "status");
		}

		@Override
		public String toString() {
			return "Assessment{status=" + status + ", refreshRequired=" + refreshRequired
					+ ", refreshCapabilityAvailable=" + refreshCapabilityAvailable + "}";
		}
	}
}
