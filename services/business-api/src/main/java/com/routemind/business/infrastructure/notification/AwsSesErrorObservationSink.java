package com.routemind.business.infrastructure.notification;

@FunctionalInterface
public interface AwsSesErrorObservationSink {

	AwsSesErrorObservationSink NO_OP = ignored -> { };

	void record(AwsSesErrorObservation observation);
}
