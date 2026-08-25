package com.routemind.business.api.preference;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.context.TestPropertySource;

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
class UserPreferenceIntegrationTests {

	private static final String TENANT_A = "10000000-0000-0000-0000-000000000001";
	private static final String TENANT_B = "20000000-0000-0000-0000-000000000002";

	@Autowired
	private MockMvc mockMvc;

	@Test
	void defaultsWritesConflictReplayAndTenantIsolationAreExplicit() throws Exception {
		mockMvc.perform(get("/api/v1/preferences/locale").header("X-Actor", "customer").with(customer(TENANT_A)))
				.andExpect(status().isOk()).andExpect(jsonPath("$.version").value(0))
				.andExpect(jsonPath("$.persisted").value(false));

		mockMvc.perform(put("/api/v1/preferences/locale").header("X-Actor", "customer").header("Idempotency-Key", "preference-locale-1").with(customer(TENANT_A))
				.contentType(MediaType.APPLICATION_JSON)
				.content("{\"expectedVersion\":0,\"values\":{\"locale\":\"zh-CN\",\"timeZone\":\"Asia/Shanghai\"}}"))
				.andExpect(status().isCreated()).andExpect(jsonPath("$.version").value(1));

		mockMvc.perform(put("/api/v1/preferences/locale").header("X-Actor", "customer").header("Idempotency-Key", "preference-locale-1").with(customer(TENANT_A))
				.contentType(MediaType.APPLICATION_JSON)
				.content("{\"expectedVersion\":0,\"values\":{\"locale\":\"zh-CN\",\"timeZone\":\"Asia/Shanghai\"}}"))
				.andExpect(status().isOk()).andExpect(jsonPath("$.replayed").value(true));

		mockMvc.perform(put("/api/v1/preferences/locale").header("X-Actor", "customer").header("Idempotency-Key", "preference-locale-2").with(customer(TENANT_A))
				.contentType(MediaType.APPLICATION_JSON)
				.content("{\"expectedVersion\":0,\"values\":{\"locale\":\"en-US\",\"timeZone\":\"UTC\"}}"))
				.andExpect(status().isConflict()).andExpect(jsonPath("$.code").value("preference_version_conflict"));

		mockMvc.perform(get("/api/v1/preferences/locale").header("X-Actor", "customer").with(customer(TENANT_B)))
				.andExpect(status().isOk()).andExpect(jsonPath("$.version").value(0));
		mockMvc.perform(get("/api/v1/preferences/locale").header("X-Actor", "merchant").with(merchant(TENANT_A)))
				.andExpect(status().isForbidden()).andExpect(jsonPath("$.code").value("preference_scope_forbidden"));
	}

	private static org.springframework.test.web.servlet.request.RequestPostProcessor customer(String tenant) {
		return jwt().authorities(new SimpleGrantedAuthority("ROLE_CUSTOMER")).jwt(token -> token.subject("subject-1").issuer("http://127.0.0.1:19090/issuer")
				.audience(List.of("routemind-business-api")).claim("jti", "token-1")
				.claim("roles", List.of("customer")).claim("tenant_id", tenant));
	}

	private static org.springframework.test.web.servlet.request.RequestPostProcessor merchant(String tenant) {
		return jwt().authorities(new SimpleGrantedAuthority("ROLE_MERCHANT")).jwt(token -> token.subject("subject-1").issuer("http://127.0.0.1:19090/issuer")
				.audience(List.of("routemind-business-api")).claim("jti", "token-2")
				.claim("roles", List.of("merchant")).claim("tenant_id", tenant));
	}
}
