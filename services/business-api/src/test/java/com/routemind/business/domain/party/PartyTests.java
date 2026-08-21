package com.routemind.business.domain.party;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Instant;
import org.junit.jupiter.api.Test;

class PartyTests {

	private static final Instant CREATED_AT = Instant.parse("2026-08-21T15:00:00Z");

	@Test
	void createsAnActivePartyWithStableAuditMetadata() {
		Party party = Party.active(new CustomerIdentity(PartyId.newId(), "customer-1", "Customer"), CREATED_AT);

		assertThat(party.status()).isEqualTo(PartyStatus.ACTIVE);
		assertThat(party.auditMetadata()).isEqualTo(new AuditMetadata(CREATED_AT, CREATED_AT));
	}

	@Test
	void renameRetainsCreationTimeAndAdvancesUpdateTime() {
		Party party = Party.active(new MerchantIdentity(PartyId.newId(), "merchant-1", "Merchant"), CREATED_AT);
		Instant renamedAt = CREATED_AT.plusSeconds(60);

		Party renamed = party.rename("Renamed Merchant", renamedAt);

		assertThat(renamed.identity()).isInstanceOf(MerchantIdentity.class);
		assertThat(renamed.identity().displayName()).isEqualTo("Renamed Merchant");
		assertThat(renamed.auditMetadata()).isEqualTo(new AuditMetadata(CREATED_AT, renamedAt));
	}

	@Test
	void rejectsAuditTimeReversalOrNonAdvancingChanges() {
		assertThatThrownBy(() -> new AuditMetadata(CREATED_AT, CREATED_AT.minusSeconds(1)))
				.isInstanceOf(IllegalArgumentException.class)
				.hasMessageContaining("before");

		Party party = Party.active(new CourierIdentity(PartyId.newId(), "courier-1", "Courier"), CREATED_AT);
		assertThatThrownBy(() -> party.rename("Courier Two", CREATED_AT))
				.isInstanceOf(IllegalArgumentException.class)
				.hasMessageContaining("advance");
	}
}
