package com.routemind.business.infrastructure.notification;

import com.routemind.business.application.notification.NotificationRecipient;
import com.routemind.business.application.notification.NotificationSender;
import java.util.Objects;
import java.util.regex.Pattern;
import org.springframework.boot.context.properties.ConfigurationProperties;

/** Non-secret SES configuration. Credential values are never represented here. */
@ConfigurationProperties("routemind.notification.ses")
public final class NotificationSesProperties {

	private static final Pattern PROFILE = Pattern.compile("^[A-Za-z0-9][A-Za-z0-9._+=,@-]{0,127}$");
	private static final Pattern REGION = Pattern.compile("^[a-z0-9][a-z0-9-]{0,62}$");

	private final boolean enabled;
	private final String profile;
	private final String region;
	private final String sender;
	private final String syntheticRecipient;

	public NotificationSesProperties(boolean enabled, String profile, String region, String sender,
			String syntheticRecipient) {
		this.enabled = enabled;
		this.profile = optionalText(profile, "profile");
		this.region = requiredRegion(region);
		this.sender = optionalText(sender, "sender");
		this.syntheticRecipient = optionalText(syntheticRecipient, "syntheticRecipient");
		if (!this.profile.isBlank() && !PROFILE.matcher(this.profile).matches()) {
			throw new IllegalArgumentException("profile has invalid characters");
		}
		if (!this.sender.isBlank()) {
			new NotificationSender(this.sender);
		}
		if (!this.syntheticRecipient.isBlank()) {
			new NotificationRecipient(this.syntheticRecipient);
		}
		if (enabled && (this.sender.isBlank() || this.syntheticRecipient.isBlank())) {
			throw new IllegalArgumentException("sender and synthetic recipient are required when SES is enabled");
		}
	}

	public boolean enabled() {
		return enabled;
	}

	public String profile() {
		return profile;
	}

	public String region() {
		return region;
	}

	/** Only the provider boundary may use this value; diagnostics must use a digest. */
	public String sender() {
		return sender;
	}

	/** Only the provider boundary may use this value; diagnostics must use a digest. */
	public String syntheticRecipient() {
		return syntheticRecipient;
	}

	public String effectiveProfile(String environmentProfile) {
		String candidate = profile.isBlank() ? optionalText(environmentProfile, "environmentProfile") : profile;
		if (!candidate.isBlank() && !PROFILE.matcher(candidate).matches()) {
			throw new IllegalArgumentException("effective AWS profile has invalid characters");
		}
		return candidate;
	}

	@Override
	public String toString() {
		return "NotificationSesProperties{enabled=" + enabled + ", profileConfigured=" + !profile.isBlank()
				+ ", region=" + region + ", senderConfigured=" + !sender.isBlank()
				+ ", syntheticRecipientConfigured=" + !syntheticRecipient.isBlank() + "}";
	}

	private static String requiredRegion(String value) {
		String normalized = optionalText(value, "region");
		if (normalized.isBlank() || !REGION.matcher(normalized).matches()) {
			throw new IllegalArgumentException("region must be a valid AWS region identifier");
		}
		return normalized;
	}

	private static String optionalText(String value, String name) {
		String normalized = Objects.requireNonNullElse(value, "").trim();
		if (normalized.length() > 320 || normalized.chars().anyMatch(Character::isISOControl)) {
			throw new IllegalArgumentException(name + " contains unsafe text");
		}
		return normalized;
	}
}
