package com.routemind.business.domain.inbox;

public enum InboxStatus {
	RECEIVED,
	PROCESSING,
	PROCESSED,
	RETRYABLE,
	DEAD_LETTER
}
