package com.routemind.business.domain.party;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.UUID;
import org.junit.jupiter.api.Test;

class PartyIdentityTests {

	private final PartyId id = new PartyId(UUID.fromString("11111111-1111-4111-8111-111111111111"));

	@Test
	void exposesAnExplicitTypeForEveryIdentity() {
		assertThat(new CustomerIdentity(id, "customer-1", "Customer").type()).isEqualTo(PartyType.CUSTOMER);
		assertThat(new MerchantIdentity(id, "merchant-1", "Merchant").type()).isEqualTo(PartyType.MERCHANT);
		assertThat(new CourierIdentity(id, "courier-1", "Courier").type()).isEqualTo(PartyType.COURIER);
	}

	@Test
	void normalizesIdentityTextAtTheBoundary() {
		CustomerIdentity identity = new CustomerIdentity(id, " customer:1 ", " Customer One ");

		assertThat(identity.externalReference()).isEqualTo("customer:1");
		assertThat(identity.displayName()).isEqualTo("Customer One");
	}

	@Test
	void rejectsUnsupportedExternalReferences() {
		assertThatThrownBy(() -> new MerchantIdentity(id, "merchant ref", "Merchant"))
				.isInstanceOf(IllegalArgumentException.class)
				.hasMessageContaining("unsupported characters");
	}

	@Test
	void rejectsBlankLongAndControlCharacterNames() {
		assertThatThrownBy(() -> new CourierIdentity(id, "courier-1", " "))
				.isInstanceOf(IllegalArgumentException.class)
				.hasMessage("displayName must not be blank");
		assertThatThrownBy(() -> new CourierIdentity(id, "courier-1", "x".repeat(121)))
				.isInstanceOf(IllegalArgumentException.class)
				.hasMessageContaining("120");
		assertThatThrownBy(() -> new CourierIdentity(id, "courier-1", "Courier\nOne"))
				.isInstanceOf(IllegalArgumentException.class)
				.hasMessageContaining("control characters");
	}

	@Test
	void rejectsMissingPartyIds() {
		assertThatThrownBy(() -> new CustomerIdentity(null, "customer-1", "Customer"))
				.isInstanceOf(NullPointerException.class)
				.hasMessage("id must not be null");
	}
}
