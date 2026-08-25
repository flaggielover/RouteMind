package com.routemind.business.infrastructure.security;

import java.time.Instant;

interface EdgeRateLimitStore {

	WindowUsage consume(String key, Instant now, long windowSeconds, long capacity);

	record WindowUsage(long used, long remaining, long retryAfterSeconds) {
		public WindowUsage {
			if (used <= 0 || remaining < 0 || retryAfterSeconds <= 0) {
				throw new IllegalArgumentException("window usage values are invalid");
			}
		}

		boolean allowed(long capacity) {
			return used <= capacity;
		}
	}
}
