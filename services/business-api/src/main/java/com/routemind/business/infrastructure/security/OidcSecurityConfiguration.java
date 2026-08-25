package com.routemind.business.infrastructure.security;

import jakarta.servlet.DispatcherType;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.oauth2.core.DelegatingOAuth2TokenValidator;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtValidators;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationConverter;
import org.springframework.security.oauth2.server.resource.web.authentication.BearerTokenAuthenticationFilter;
import org.springframework.security.web.SecurityFilterChain;

@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties(OidcSecurityProperties.class)
@ConditionalOnProperty(name = "routemind.security.oidc.enabled", havingValue = "true")
public class OidcSecurityConfiguration {

	@Bean
	JwtDecoder oidcJwtDecoder(OidcSecurityProperties properties) {
		NimbusJwtDecoder decoder = NimbusJwtDecoder.withJwkSetUri(properties.jwkSetUri().toString()).build();
		decoder.setJwtValidator(new DelegatingOAuth2TokenValidator<>(
				JwtValidators.createDefaultWithIssuer(properties.issuer().toString()),
				new OidcAudienceValidator(properties.audience()),
				new OidcRequiredClaimsValidator(properties.rolesClaim(), properties.tenantClaim())));
		return decoder;
	}

	@Bean
	OidcPrincipalMapper oidcPrincipalMapper(OidcSecurityProperties properties) {
		return new OidcPrincipalMapper(properties);
	}

	@Bean
	SecurityFilterChain oidcSecurityFilterChain(HttpSecurity http, JwtDecoder decoder,
			OidcSecurityProperties properties,
			com.routemind.business.application.security.TenantContext tenants) throws Exception {
		JwtAuthenticationConverter authenticationConverter = new JwtAuthenticationConverter();
		authenticationConverter.setJwtGrantedAuthoritiesConverter(new OidcAuthorityConverter(properties.rolesClaim()));
		http.csrf(csrf -> csrf.disable())
				.cors(Customizer.withDefaults())
				.sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
				.requestCache(cache -> cache.disable())
				.logout(logout -> logout.disable())
				.addFilterAfter(TenantContextFilter.oidc(tenants, properties.tenantClaim()),
						BearerTokenAuthenticationFilter.class)
				.addFilterAfter(new OidcActorBindingFilter(), TenantContextFilter.class)
				.authorizeHttpRequests(authorize -> authorize
						.dispatcherTypeMatchers(DispatcherType.ERROR).permitAll()
						.requestMatchers("/actuator/health", "/actuator/health/**", "/actuator/info").permitAll()
						.requestMatchers("/api/**", "/metrics").authenticated()
						.anyRequest().denyAll())
				.oauth2ResourceServer(resource -> resource.jwt(jwt -> jwt.decoder(decoder)
						.jwtAuthenticationConverter(authenticationConverter)));
		return http.build();
	}
}
