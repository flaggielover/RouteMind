package com.routemind.business.application.realtime;

public final class EventStreamStaleException extends RuntimeException {

	public EventStreamStaleException(String message) {
		super(message);
	}
}
