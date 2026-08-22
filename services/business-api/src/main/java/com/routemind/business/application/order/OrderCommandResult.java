package com.routemind.business.application.order;

import java.util.UUID;

public record OrderCommandResult(UUID orderId, String status, long version, boolean replayed) {

	public OrderCommandResult {
		if (orderId == null || status == null || status.isBlank() || version < 0) {
			throw new IllegalArgumentException("command result fields are required");
		}
	}
}
