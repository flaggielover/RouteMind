package com.routemind.business.infrastructure.config;

import com.routemind.business.application.system.GetSystemInfoUseCase;
import com.routemind.business.application.system.SystemInfoService;
import com.routemind.business.domain.system.ServiceIdentity;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration(proxyBeanMethods = false)
public class SystemModuleConfiguration {

	@Bean
	ServiceIdentity businessServiceIdentity() {
		return new ServiceIdentity("business-api", "java", "v1");
	}

	@Bean
	GetSystemInfoUseCase getSystemInfoUseCase(ServiceIdentity serviceIdentity) {
		return new SystemInfoService(serviceIdentity);
	}
}
