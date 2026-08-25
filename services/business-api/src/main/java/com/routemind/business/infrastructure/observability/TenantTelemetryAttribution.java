package com.routemind.business.infrastructure.observability;

import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.util.HexFormat;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.UUID;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

import com.routemind.business.application.observability.TelemetryAttribution;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public final class TenantTelemetryAttribution implements TelemetryAttribution {

	private static final HexFormat HEX = HexFormat.of();

	private final byte[] secret;
	private final int maximumActiveKeys;
	private final MeterRegistry meterRegistry;
	private final Set<String> activeKeys = new LinkedHashSet<>();

	public TenantTelemetryAttribution(
			@Value("${routemind.telemetry.attribution-key:change-me-local-only-telemetry-attribution-key}") String secret,
			@Value("${routemind.telemetry.max-tenant-keys:64}") int maximumActiveKeys,
			MeterRegistry meterRegistry) {
		if (secret == null || secret.length() < 32) {
			throw new IllegalArgumentException("telemetry attribution key must contain at least 32 characters");
		}
		if (maximumActiveKeys < 1 || maximumActiveKeys > 256) {
			throw new IllegalArgumentException("maximum telemetry tenant keys must be between 1 and 256");
		}
		this.secret = secret.getBytes(StandardCharsets.UTF_8);
		this.maximumActiveKeys = maximumActiveKeys;
		this.meterRegistry = meterRegistry;
	}

	@Override
	public synchronized String tenantKey(UUID tenantId) {
		String candidate = "rtk_" + hmac(tenantId.toString());
		if (activeKeys.contains(candidate)) {
			return candidate;
		}
		if (activeKeys.size() >= maximumActiveKeys) {
			return OVERFLOW_KEY;
		}
		activeKeys.add(candidate);
		return candidate;
	}

	@Override
	public void record(String signal, String operation, String tenantKey) {
		meterRegistry.counter("routemind.telemetry.attributed.records",
				"service", "business-api", "signal", bounded(signal), "operation", bounded(operation),
				"tenant_key", tenantKey).increment();
	}

	public synchronized int activeKeyCount() {
		return activeKeys.size();
	}

	private String hmac(String value) {
		try {
			Mac mac = Mac.getInstance("HmacSHA256");
			mac.init(new SecretKeySpec(secret, "HmacSHA256"));
			byte[] digest = mac.doFinal(value.getBytes(StandardCharsets.UTF_8));
			return HEX.formatHex(digest, 0, 12);
		}
		catch (GeneralSecurityException exception) {
			throw new IllegalStateException("HMAC-SHA256 is unavailable", exception);
		}
	}

	private static String bounded(String value) {
		if (value == null || !value.matches("[a-z][a-z0-9_.-]{0,31}")) {
			throw new IllegalArgumentException("telemetry dimension is invalid");
		}
		return value;
	}
}
