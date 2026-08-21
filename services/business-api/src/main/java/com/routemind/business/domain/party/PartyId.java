package com.routemind.business.domain.party;

import java.util.Objects;
import java.util.UUID;

public record PartyId(UUID value) {

	public PartyId {
		Objects.requireNonNull(value, "value must not be null");
	}

	public static PartyId newId() {
		return new PartyId(UUID.randomUUID());
	}
}
