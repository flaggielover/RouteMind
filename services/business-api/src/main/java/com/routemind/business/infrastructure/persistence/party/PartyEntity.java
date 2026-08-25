package com.routemind.business.infrastructure.persistence.party;

import com.routemind.business.domain.party.AuditMetadata;
import com.routemind.business.domain.party.CourierIdentity;
import com.routemind.business.domain.party.CustomerIdentity;
import com.routemind.business.domain.party.MerchantIdentity;
import com.routemind.business.domain.party.Party;
import com.routemind.business.domain.party.PartyId;
import com.routemind.business.domain.party.PartyIdentity;
import com.routemind.business.domain.party.PartyStatus;
import com.routemind.business.domain.party.PartyType;
import com.routemind.business.infrastructure.persistence.TenantScopedEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "parties", schema = "routemind")
class PartyEntity extends TenantScopedEntity {

	@Id
	private UUID id;

	@Enumerated(EnumType.STRING)
	@Column(name = "party_type", nullable = false, length = 16)
	private PartyType partyType;

	@Column(name = "external_reference", nullable = false, length = 64)
	private String externalReference;

	@Column(name = "display_name", nullable = false, length = 120)
	private String displayName;

	@Enumerated(EnumType.STRING)
	@Column(nullable = false, length = 16)
	private PartyStatus status;

	@Column(name = "created_at", nullable = false)
	private Instant createdAt;

	@Column(name = "updated_at", nullable = false)
	private Instant updatedAt;

	@Version
	@Column(nullable = false)
	private Long version;

	protected PartyEntity() {
	}

	private PartyEntity(Party party, UUID tenantId) {
		assignTenant(tenantId);
		this.id = party.id().value();
		apply(party);
	}

	static PartyEntity from(Party party, UUID tenantId) {
		return new PartyEntity(party, tenantId);
	}

	void apply(Party party) {
		if (id != null && !id.equals(party.id().value())) {
			throw new IllegalArgumentException("party identity cannot change");
		}
		id = party.id().value();
		partyType = party.identity().type();
		externalReference = party.identity().externalReference();
		displayName = party.identity().displayName();
		status = party.status();
		createdAt = party.auditMetadata().createdAt();
		updatedAt = party.auditMetadata().updatedAt();
	}

	Party toDomain() {
		PartyId partyId = new PartyId(id);
		PartyIdentity identity = switch (partyType) {
			case CUSTOMER -> new CustomerIdentity(partyId, externalReference, displayName);
			case MERCHANT -> new MerchantIdentity(partyId, externalReference, displayName);
			case COURIER -> new CourierIdentity(partyId, externalReference, displayName);
		};
		return new Party(identity, status, new AuditMetadata(createdAt, updatedAt));
	}
}
