package com.routemind.business.application.order;

public final class OrderCommandConflictException extends RuntimeException {

	public OrderCommandConflictException(String reason) {
		super(reason);
	}
}
