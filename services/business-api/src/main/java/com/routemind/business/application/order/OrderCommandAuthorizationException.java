package com.routemind.business.application.order;

public final class OrderCommandAuthorizationException extends RuntimeException {

	public OrderCommandAuthorizationException(String reason) {
		super(reason);
	}
}
