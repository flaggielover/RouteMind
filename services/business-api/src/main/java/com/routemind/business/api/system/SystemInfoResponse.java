package com.routemind.business.api.system;

import com.routemind.business.domain.system.ServiceIdentity;

public record SystemInfoResponse(String service, String runtime, String architectureVersion) {

	static SystemInfoResponse from(ServiceIdentity identity) {
		return new SystemInfoResponse(identity.name(), identity.runtime(), identity.architectureVersion());
	}
}
