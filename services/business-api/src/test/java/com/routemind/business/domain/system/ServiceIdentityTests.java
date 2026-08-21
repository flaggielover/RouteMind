package com.routemind.business.domain.system;

import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class ServiceIdentityTests {

	@Test
	void rejectsBlankIdentityFields() {
		assertThatThrownBy(() -> new ServiceIdentity("business-api", " ", "v1"))
				.isInstanceOf(IllegalArgumentException.class)
				.hasMessage("runtime must not be blank");
	}
}
