package com.routemind.business.application.realtime;

public interface EventStreamRepository {

	EventStreamPage recent(int limit);
}
