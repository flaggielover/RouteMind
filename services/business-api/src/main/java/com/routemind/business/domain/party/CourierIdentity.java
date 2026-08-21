package com.routemind.business.domain.party;

import java.util.Objects;

public record CourierIdentity(PartyId id, String externalReference, String displayName) implements PartyIdentity {

	public CourierIdentity {
		Objects.requireNonNull(id, "id must not be null");
		externalReference = PartyText.externalReference(externalReference);
		displayName = PartyText.displayName(displayName);
	}

	@Override
	public PartyType type() {
		return PartyType.COURIER;
	}

	@Override
	public CourierIdentity withDisplayName(String newDisplayName) {
		return new CourierIdentity(id, externalReference, newDisplayName);
	}
}
