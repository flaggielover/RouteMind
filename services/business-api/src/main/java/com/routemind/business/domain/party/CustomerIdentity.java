package com.routemind.business.domain.party;

import java.util.Objects;

public record CustomerIdentity(PartyId id, String externalReference, String displayName) implements PartyIdentity {

	public CustomerIdentity {
		Objects.requireNonNull(id, "id must not be null");
		externalReference = PartyText.externalReference(externalReference);
		displayName = PartyText.displayName(displayName);
	}

	@Override
	public PartyType type() {
		return PartyType.CUSTOMER;
	}

	@Override
	public CustomerIdentity withDisplayName(String newDisplayName) {
		return new CustomerIdentity(id, externalReference, newDisplayName);
	}
}
