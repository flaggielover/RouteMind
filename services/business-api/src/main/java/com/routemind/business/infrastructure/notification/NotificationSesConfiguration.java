package com.routemind.business.infrastructure.notification;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties(NotificationSesProperties.class)
public class NotificationSesConfiguration {

	@Bean
	AwsSesCredentialProviderFactory awsSesCredentialProviderFactory() {
		return new AwsSesCredentialProviderFactory();
	}

	@Bean
	AwsSesClientFactory awsSesClientFactory(AwsSesCredentialProviderFactory credentials) {
		return new AwsSesClientFactory(credentials);
	}
}
