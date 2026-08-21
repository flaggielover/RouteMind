package com.routemind.business.infrastructure.persistence.party;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.routemind.business.application.party.PartyRepository;
import com.routemind.business.domain.party.CourierIdentity;
import com.routemind.business.domain.party.CustomerIdentity;
import com.routemind.business.domain.party.MerchantIdentity;
import com.routemind.business.domain.party.Party;
import com.routemind.business.domain.party.PartyId;
import com.routemind.business.domain.party.PartyIdentity;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class PartyRepositoryTests {

	private static final Instant CREATED_AT = Instant.parse("2026-08-21T15:00:00Z");

	@Autowired
	private PartyRepository repository;

	@Autowired
	private JdbcTemplate jdbcTemplate;

	@BeforeEach
	void clearParties() {
		jdbcTemplate.update("delete from routemind.parties");
	}

	@Test
	void roundTripsEveryExplicitIdentityTypeAndAuditMetadata() {
		List<PartyIdentity> identities = List.of(
				new CustomerIdentity(PartyId.newId(), "shared-1", "Customer"),
				new MerchantIdentity(PartyId.newId(), "shared-1", "Merchant"),
				new CourierIdentity(PartyId.newId(), "shared-1", "Courier"));

		for (PartyIdentity identity : identities) {
			Party party = Party.active(identity, CREATED_AT);

			assertThat(repository.save(party)).isEqualTo(party);
			assertThat(repository.findById(party.id())).contains(party);
		}
	}

	@Test
	void enforcesExternalReferenceUniquenessWithinARole() {
		repository.save(Party.active(
				new CustomerIdentity(PartyId.newId(), "customer-1", "Customer One"), CREATED_AT));

		Party duplicate = Party.active(
				new CustomerIdentity(PartyId.newId(), "customer-1", "Customer Two"), CREATED_AT);

		assertThatThrownBy(() -> repository.save(duplicate))
				.isInstanceOf(DataIntegrityViolationException.class);
	}

	@Test
	void updatingAPartyRetainsCreationAuditMetadata() {
		Party original = Party.active(
				new MerchantIdentity(PartyId.newId(), "merchant-1", "Merchant"), CREATED_AT);
		repository.save(original);

		Instant renamedAt = CREATED_AT.plusSeconds(90);
		Party renamed = repository.save(original.rename("Renamed Merchant", renamedAt));

		assertThat(renamed.auditMetadata().createdAt()).isEqualTo(CREATED_AT);
		assertThat(renamed.auditMetadata().updatedAt()).isEqualTo(renamedAt);
		assertThat(repository.findById(original.id())).contains(renamed);
	}
}
