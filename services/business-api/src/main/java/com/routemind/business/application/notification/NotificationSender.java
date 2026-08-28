package com.routemind.business.application.notification;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Objects;
import java.util.regex.Pattern;

public final class NotificationSender {

	private static final Pattern EMAIL = Pattern.compile("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$");
	private final String address;

	public NotificationSender(String address) {
		String value = Objects.requireNonNull(address, "address").trim();
		if (value.length() > 320 || !EMAIL.matcher(value).matches()) {
			throw new IllegalArgumentException("sender email is invalid");
		}
		this.address = value;
	}

	/** Only a provider adapter may use this value; all diagnostics use digest(). */
	public String address() {
		return address;
	}

	public String digest() {
		try {
			return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
					.digest(address.getBytes(StandardCharsets.UTF_8)));
		}
		catch (NoSuchAlgorithmException exception) {
			throw new IllegalStateException("SHA-256 is unavailable", exception);
		}
	}

	@Override
	public String toString() {
		return "NotificationSender{digest=" + digest().substring(0, 16) + "}";
	}

	@Override
	public boolean equals(Object other) {
		return other instanceof NotificationSender sender && address.equals(sender.address);
	}

	@Override
	public int hashCode() {
		return address.hashCode();
	}
}
