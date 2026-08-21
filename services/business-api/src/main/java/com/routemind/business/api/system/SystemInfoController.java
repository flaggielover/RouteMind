package com.routemind.business.api.system;

import com.routemind.business.application.system.GetSystemInfoUseCase;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/system")
public final class SystemInfoController {

	private final GetSystemInfoUseCase getSystemInfo;

	public SystemInfoController(GetSystemInfoUseCase getSystemInfo) {
		this.getSystemInfo = getSystemInfo;
	}

	@GetMapping
	public SystemInfoResponse getSystemInfo() {
		return SystemInfoResponse.from(getSystemInfo.getSystemInfo());
	}
}
