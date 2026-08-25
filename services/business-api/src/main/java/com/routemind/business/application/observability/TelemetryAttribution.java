package com.routemind.business.application.observability;

import java.util.UUID;

public interface TelemetryAttribution {

	String REQUEST_ATTRIBUTE = "routemind.telemetry.tenant_key";
	String UNATTRIBUTED_KEY = "rtk_unattributed";
	String OVERFLOW_KEY = "rtk_overflow";

	String tenantKey(UUID tenantId);

	void record(String signal, String operation, String tenantKey);
}
