package com.routemind.business.infrastructure.security;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;

@Configuration(proxyBeanMethods = false)
@ConditionalOnProperty(name = "routemind.security.oidc.enabled", havingValue = "false", matchIfMissing = true)
public class LocalSecurityConfiguration {

	@Bean
	SecurityFilterChain localCompatibilitySecurityFilterChain(HttpSecurity http) throws Exception {
		http.csrf(csrf -> csrf.disable())
				.sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
				.requestCache(cache -> cache.disable())
				.logout(logout -> logout.disable())
				.authorizeHttpRequests(authorize -> authorize.anyRequest().permitAll());
		return http.build();
	}
}
