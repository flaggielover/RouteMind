package com.routemind.business.infrastructure.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.security.core.authority.SimpleGrantedAuthority;

class EdgeSecurityPropertiesTests {

	@Test
	void verifiedRolesSelectTheirExplicitQuota() {
		EdgeSecurityProperties properties = properties();
		assertThat(properties.roleLimit(List.of(new SimpleGrantedAuthority("ROLE_CUSTOMER")), true).requests())
				.isEqualTo(180);
		assertThat(properties.roleLimit(List.of(new SimpleGrantedAuthority("ROLE_CUSTOMER"),
				new SimpleGrantedAuthority("ROLE_OPERATOR")), true).role()).isEqualTo("operator");
		assertThat(properties.roleLimit(List.of(), false).role()).isEqualTo("anonymous");
	}

	@Test
	void invalidOrUnversionedLimitsFailConfiguration() {
		assertThatThrownBy(() -> new EdgeSecurityProperties(true, " ", 60, 1, 1, 1, 1, 1, 1, 1, 1,
				1, 1, 1, 1, 1, 1)).isInstanceOf(IllegalArgumentException.class);
		assertThatThrownBy(() -> new EdgeSecurityProperties(true, "edge-v1", 0, 1, 1, 1, 1, 1, 1, 1, 1,
				1, 1, 1, 1, 1, 1)).isInstanceOf(IllegalArgumentException.class);
		assertThatThrownBy(() -> new EdgeSecurityProperties(true, "edge-v1", 60, 1, 1, 1, 1, 1, 1, 1, 1,
				1, 1, 1, 1, 1, Integer.MAX_VALUE))
				.isInstanceOf(IllegalArgumentException.class)
				.hasMessageContaining("bounded request buffer");
	}

	private static EdgeSecurityProperties properties() {
		return new EdgeSecurityProperties(true, "edge-v1", 60, 20, 60, 120, 180, 300, 240, 300, 600,
				10000, 64, 16384, 4096, 2048, 1048576);
	}
}
