package com.routemind.business.infrastructure.security;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;

import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.security.core.authority.SimpleGrantedAuthority;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@TestPropertySource(properties = {
		"routemind.security.oidc.enabled=true",
		"routemind.security.oidc.issuer=http://127.0.0.1:19090/issuer",
		"routemind.security.oidc.audience=routemind-business-api",
		"routemind.security.oidc.jwk-set-uri=http://127.0.0.1:19090/jwks",
		"routemind.security.oidc.allow-insecure-loopback=true"
})
class OidcSecurityIntegrationTests {

	@Autowired
	private MockMvc mockMvc;

	@Test
	void healthIsAnonymousButBusinessAndMetricsEndpointsRequireBearerIdentity() throws Exception {
		mockMvc.perform(get("/actuator/health")).andExpect(status().isOk());
		mockMvc.perform(get("/api/v1/system")).andExpect(status().isUnauthorized());
		mockMvc.perform(get("/metrics")).andExpect(status().isUnauthorized());
	}

	@Test
	void validatedJwtReachesBusinessApiWhileUnknownRoutesDenyByDefault() throws Exception {
		mockMvc.perform(get("/api/v1/system").with(jwt().jwt(token -> token
				.subject("operator-1")
				.issuer("http://127.0.0.1:19090/issuer")
				.audience(List.of("routemind-business-api"))
				.claim("jti", "token-1")
				.claim("roles", List.of("operator"))
				.claim("scope", "system:read")
				.claim("tenant_id", "10000000-0000-0000-0000-000000000001")
				.issuedAt(Instant.now().minusSeconds(30))
				.expiresAt(Instant.now().plusSeconds(300)))))
				.andExpect(status().isOk())
				.andExpect(header().string("X-Edge-Policy", "edge-v1"))
				.andExpect(header().string("X-RateLimit-Mode", "primary"));
		mockMvc.perform(get("/not-an-endpoint").with(jwt())).andExpect(status().isForbidden());
	}

	@Test
	void actorHeaderMustMatchAVerifiedTokenRole() throws Exception {
		var operator = jwt().jwt(token -> token
				.claim("tenant_id", "10000000-0000-0000-0000-000000000001"))
				.authorities(new SimpleGrantedAuthority("ROLE_OPERATOR"));

		mockMvc.perform(get("/api/v1/system").header("X-Actor", "operator").with(operator))
				.andExpect(status().isOk());
		mockMvc.perform(get("/api/v1/system").header("X-Actor", "customer").with(operator))
				.andExpect(status().isForbidden());
		mockMvc.perform(get("/api/v1/system")
				.header("X-Tenant-Id", "20000000-0000-0000-0000-000000000002").with(operator))
				.andExpect(status().isForbidden());
	}
}
