package com.routemind.business.domain.outbox;

public enum OutboxStatus {
	PENDING,
	IN_FLIGHT,
	PUBLISHED,
	RETRYABLE
}
