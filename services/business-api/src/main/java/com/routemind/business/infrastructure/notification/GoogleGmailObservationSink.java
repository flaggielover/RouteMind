package com.routemind.business.infrastructure.notification;

@FunctionalInterface
public interface GoogleGmailObservationSink {

	GoogleGmailObservationSink NO_OP = ignored -> { };

	void record(GoogleGmailErrorObservation observation);
}
