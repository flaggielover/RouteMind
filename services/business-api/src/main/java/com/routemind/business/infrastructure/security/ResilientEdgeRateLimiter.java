package com.routemind.business.infrastructure.security;

import java.time.Instant;
import java.util.Objects;

final class ResilientEdgeRateLimiter {

	private final EdgeRateLimitStore primary;
	private final EdgeRateLimitStore fallback;

	ResilientEdgeRateLimiter(EdgeRateLimitStore primary, EdgeRateLimitStore fallback) {
		this.primary = Objects.requireNonNull(primary, "primary");
		this.fallback = Objects.requireNonNull(fallback, "fallback");
	}

	LimitDecision consume(String key, Instant now, long windowSeconds, long capacity) {
		try {
			return decision(primary.consume(key, now, windowSeconds, capacity), capacity, "primary");
		}
		catch (RuntimeException primaryFailure) {
			try {
				return decision(fallback.consume(key, now, windowSeconds, capacity), capacity, "fallback");
			}
			catch (RuntimeException fallbackFailure) {
				return new LimitDecision(false, 0, 1, "unavailable", true);
			}
		}
	}

	private static LimitDecision decision(EdgeRateLimitStore.WindowUsage usage, long capacity, String mode) {
		return new LimitDecision(usage.allowed(capacity), usage.remaining(), usage.retryAfterSeconds(), mode, false);
	}

	record LimitDecision(boolean allowed, long remaining, long retryAfterSeconds, String mode, boolean unavailable) {
		LimitDecision {
			if (remaining < 0 || retryAfterSeconds <= 0 || mode == null || mode.isBlank()) {
				throw new IllegalArgumentException("limit decision values are invalid");
			}
		}
	}
}
