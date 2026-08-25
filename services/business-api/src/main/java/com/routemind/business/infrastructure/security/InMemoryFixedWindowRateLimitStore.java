package com.routemind.business.infrastructure.security;

import java.time.Instant;
import java.util.Objects;
import java.util.concurrent.ConcurrentHashMap;

final class InMemoryFixedWindowRateLimitStore implements EdgeRateLimitStore {

	private final int maxTrackedKeys;
	private final ConcurrentHashMap<String, WindowCounter> counters = new ConcurrentHashMap<>();

	InMemoryFixedWindowRateLimitStore(int maxTrackedKeys) {
		if (maxTrackedKeys <= 0) {
			throw new IllegalArgumentException("maxTrackedKeys must be positive");
		}
		this.maxTrackedKeys = maxTrackedKeys;
	}

	@Override
	public synchronized WindowUsage consume(String key, Instant now, long windowSeconds, long capacity) {
		Objects.requireNonNull(key, "key");
		Objects.requireNonNull(now, "now");
		if (key.isBlank() || windowSeconds <= 0 || capacity <= 0) {
			throw new IllegalArgumentException("rate-limit request is invalid");
		}
		long window = Math.floorDiv(now.getEpochSecond(), windowSeconds);
		if (!counters.containsKey(key) && counters.size() >= maxTrackedKeys) {
			counters.entrySet().removeIf(entry -> entry.getValue().window() < window);
			if (counters.size() >= maxTrackedKeys) {
				throw new IllegalStateException("rate-limit key capacity exhausted");
			}
		}
		WindowCounter counter = counters.compute(key, (ignored, previous) -> previous == null || previous.window() != window
				? new WindowCounter(window, 1)
				: new WindowCounter(window, previous.used() + 1));
		long remaining = Math.max(0, capacity - counter.used());
		long retryAfter = Math.max(1, ((window + 1) * windowSeconds) - now.getEpochSecond());
		return new WindowUsage(counter.used(), remaining, retryAfter);
	}

	private record WindowCounter(long window, long used) {
	}
}
