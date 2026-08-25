package com.routemind.business.application.preference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class PreferencePayloadPolicyTests {

	private PreferencePayloadPolicy policy;
	private ObjectMapper mapper;

	@BeforeEach
	void setUp() {
		mapper = new ObjectMapper();
		policy = new PreferencePayloadPolicy(mapper);
	}

	@Test
	void defaultsAreDeterministicAndNamespaceSpecific() {
		assertThat(policy.defaults(PreferenceNamespace.LOCALE)).isEqualTo("{\"locale\":\"en-US\",\"timeZone\":\"UTC\"}");
		assertThat(policy.defaults(PreferenceNamespace.NOTIFICATIONS)).contains("\"in_app\":true");
	}

	@Test
	void canonicalizesAllowedAccessibilityValuesAndRejectsUnknownFields() throws Exception {
		String value = policy.canonicalize(PreferenceNamespace.ACCESSIBILITY, mapper.readTree("""
				{"theme":"dark","contrast":"high","reducedMotion":"reduce","textScale":1.25,
				 "screenReaderAnnouncements":"polite","visibleFocus":true,"colorOnlyStatus":false}
				"""));
		assertThat(value).contains("\"theme\":\"dark\"").contains("\"textScale\":1.25");
		assertThatThrownBy(() -> policy.canonicalize(PreferenceNamespace.ACCESSIBILITY,
				mapper.readTree("{\"theme\":\"dark\",\"contrast\":\"high\",\"reducedMotion\":\"reduce\",\"textScale\":1,\"screenReaderAnnouncements\":\"polite\",\"visibleFocus\":true,\"colorOnlyStatus\":false,\"extra\":true}")))
				.isInstanceOf(IllegalArgumentException.class).hasMessage("preference_value_invalid");
	}

	@Test
	void rejectsInvalidTimeZoneQuietHoursAndChannelTypes() throws Exception {
		assertThatThrownBy(() -> policy.canonicalize(PreferenceNamespace.LOCALE,
				mapper.readTree("{\"locale\":\"en-US\",\"timeZone\":\"Not/AZone\"}")))
				.isInstanceOf(IllegalArgumentException.class);
		assertThatThrownBy(() -> policy.canonicalize(PreferenceNamespace.NOTIFICATIONS,
				mapper.readTree("{\"in_app\":\"yes\",\"email\":false,\"sms\":false,\"push\":false}")))
				.isInstanceOf(IllegalArgumentException.class);
	}
}
