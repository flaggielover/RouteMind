package com.routemind.business.application.courier;

public final class CourierCommandConflictException extends RuntimeException {

	public CourierCommandConflictException(String message) {
		super(message);
	}
}
