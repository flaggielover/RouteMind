package com.routemind.business.application.system;

import com.routemind.business.domain.system.ServiceIdentity;

public final class SystemInfoService implements GetSystemInfoUseCase {

	private final ServiceIdentity serviceIdentity;

	public SystemInfoService(ServiceIdentity serviceIdentity) {
		this.serviceIdentity = serviceIdentity;
	}

	@Override
	public ServiceIdentity getSystemInfo() {
		return serviceIdentity;
	}
}
