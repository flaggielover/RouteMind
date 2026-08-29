package com.routemind.business.infrastructure.notification;

import com.routemind.business.application.notification.NotificationRecipient;
import com.routemind.business.application.notification.NotificationSender;
import java.util.Objects;
import java.util.regex.Pattern;
import org.springframework.boot.context.properties.ConfigurationProperties;

/** Non-secret Gmail configuration. OAuth material is referenced, never represented. */
@ConfigurationProperties("routemind.notification.gmail")
public final class NotificationGmailProperties {

	private static final Pattern REGION = Pattern.compile("^[A-Za-z0-9][A-Za-z0-9._-]{0,31}$");

	private final boolean enabled;
	private final String region;
	private final String clientSecretsPath;
	private final String tokenStorePath;
	private final String oauthUserId;
	private final String sender;
	private final String syntheticRecipient;

	public NotificationGmailProperties(boolean enabled, String region, String clientSecretsPath,
			String tokenStorePath, String oauthUserId, String sender, String syntheticRecipient) {
		this.enabled = enabled;
		this.region = safeText(region, "region");
		if (this.region.isBlank() || !REGION.matcher(this.region).matches()) {
			throw new IllegalArgumentException("region must be a safe provider-region label");
		}
		this.clientSecretsPath = safeText(clientSecretsPath, "clientSecretsPath");
		this.tokenStorePath = safeText(tokenStorePath, "tokenStorePath");
		this.oauthUserId = safeText(oauthUserId, "oauthUserId");
		this.sender = safeText(sender, "sender");
		this.syntheticRecipient = safeText(syntheticRecipient, "syntheticRecipient");
		if (!this.sender.isBlank()) new NotificationSender(this.sender);
		if (!this.syntheticRecipient.isBlank()) new NotificationRecipient(this.syntheticRecipient);
		if (enabled && (this.clientSecretsPath.isBlank() || this.tokenStorePath.isBlank()
				|| this.oauthUserId.isBlank() || this.sender.isBlank() || this.syntheticRecipient.isBlank())) {
			throw new IllegalArgumentException("enabled Gmail requires external OAuth paths, user, sender, and recipient");
		}
	}

	public boolean enabled() { return enabled; }

	public String region() { return region; }

	public String clientSecretsPath() { return clientSecretsPath; }

	public String tokenStorePath() { return tokenStorePath; }

	public String oauthUserId() { return oauthUserId; }

	/** Provider boundary only; diagnostics must use endpoint digests. */
	public String sender() { return sender; }

	/** Provider boundary only; diagnostics must use endpoint digests. */
	public String syntheticRecipient() { return syntheticRecipient; }

	@Override
	public String toString() {
		return "NotificationGmailProperties{enabled=" + enabled + ", region=" + region
				+ ", clientSecretsConfigured=" + !clientSecretsPath.isBlank()
				+ ", tokenStoreConfigured=" + !tokenStorePath.isBlank()
				+ ", oauthUserConfigured=" + !oauthUserId.isBlank()
				+ ", senderConfigured=" + !sender.isBlank()
				+ ", syntheticRecipientConfigured=" + !syntheticRecipient.isBlank() + "}";
	}

	private static String safeText(String value, String name) {
		String normalized = Objects.requireNonNullElse(value, "").trim();
		if (normalized.length() > 1024 || normalized.chars().anyMatch(Character::isISOControl)) {
			throw new IllegalArgumentException(name + " contains unsafe text");
		}
		return normalized;
	}
}
