package com.routemind.business.infrastructure.notification;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties(NotificationGmailProperties.class)
public class NotificationGmailConfiguration {

	@Bean
	GoogleGmailClientFactory googleGmailClientFactory() {
		return new GoogleGmailClientFactory();
	}
}
