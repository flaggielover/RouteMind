package com.routemind.business.infrastructure.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.net.URI;
import org.junit.jupiter.api.Test;

class OidcSecurityPropertiesTests {

	@Test
	void acceptsSameAuthorityHttpsConfiguration() {
		OidcSecurityProperties properties = enabled("https://identity.example/issuer",
				"https://identity.example/.well-known/jwks.json", false);

		assertThat(properties.audience()).isEqualTo("routemind-business-api");
		assertThat(properties.rolesClaim()).isEqualTo("roles");
	}

	@Test
	void rejectsInsecureRemoteAndConfusedAuthorityConfiguration() {
		assertThatThrownBy(() -> enabled("http://identity.example/issuer",
				"http://identity.example/jwks", false)).hasMessageContaining("HTTPS");
		assertThatThrownBy(() -> enabled("https://identity.example/issuer",
				"https://attacker.example/jwks", false)).hasMessageContaining("same authority");
	}

	@Test
	void permitsHttpOnlyForExplicitLoopbackTesting() {
		assertThat(enabled("http://127.0.0.1:19090/issuer", "http://127.0.0.1:19090/jwks", true).enabled())
				.isTrue();
		assertThatThrownBy(() -> enabled("http://127.0.0.1:19090/issuer",
				"http://127.0.0.1:19090/jwks", false)).hasMessageContaining("HTTPS");
	}

	private static OidcSecurityProperties enabled(String issuer, String jwks, boolean allowLoopback) {
		return new OidcSecurityProperties(true, URI.create(issuer), "routemind-business-api", URI.create(jwks),
				"roles", allowLoopback);
	}
}
