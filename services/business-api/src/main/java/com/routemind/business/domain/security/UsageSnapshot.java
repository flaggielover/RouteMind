package com.routemind.business.domain.security;

public record UsageSnapshot(long usedRequests, long windowElapsedSeconds) {

	public UsageSnapshot {
		if (usedRequests < 0 || windowElapsedSeconds < 0) {
			throw new IllegalArgumentException("usage measurements must be non-negative");
		}
	}
}
