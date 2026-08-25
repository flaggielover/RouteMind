package com.routemind.business.infrastructure.security;

import com.routemind.business.application.security.TenantContext;
import java.time.Clock;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties(EdgeSecurityProperties.class)
public class EdgeSecurityConfiguration {

	@Bean
	ResilientEdgeRateLimiter edgeRateLimiter(EdgeSecurityProperties properties) {
		return new ResilientEdgeRateLimiter(
				new InMemoryFixedWindowRateLimitStore(properties.maxTrackedKeys()),
				new InMemoryFixedWindowRateLimitStore(properties.maxTrackedKeys()));
	}

	@Bean
	EdgeSecurityFilter edgeSecurityFilter(TenantContext tenants, EdgeSecurityProperties properties,
			ResilientEdgeRateLimiter limiter, Clock clock) {
		return new EdgeSecurityFilter(tenants, properties, limiter, clock);
	}

	@Bean
	FilterRegistrationBean<EdgeSecurityFilter> disableContainerEdgeFilterRegistration(EdgeSecurityFilter filter) {
		FilterRegistrationBean<EdgeSecurityFilter> registration = new FilterRegistrationBean<>(filter);
		registration.setEnabled(false);
		return registration;
	}
}
