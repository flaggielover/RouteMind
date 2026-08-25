package com.routemind.business.infrastructure.persistence;

import com.routemind.business.domain.security.TenantId;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.UUID;

public final class TenantKey {

	private TenantKey() {
	}

	public static String encode(UUID tenantId, String logicalKey) {
		if (TenantId.LEGACY.value().equals(tenantId)) {
			return logicalKey;
		}
		try {
			return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
					.digest((tenantId + ":" + logicalKey).getBytes(StandardCharsets.UTF_8)));
		}
		catch (NoSuchAlgorithmException exception) {
			throw new IllegalStateException("SHA-256 is unavailable", exception);
		}
	}
}
