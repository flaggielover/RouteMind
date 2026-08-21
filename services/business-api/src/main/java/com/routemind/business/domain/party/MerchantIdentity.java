package com.routemind.business.domain.party;

import java.util.Objects;

public record MerchantIdentity(PartyId id, String externalReference, String displayName) implements PartyIdentity {

	public MerchantIdentity {
		Objects.requireNonNull(id, "id must not be null");
		externalReference = PartyText.externalReference(externalReference);
		displayName = PartyText.displayName(displayName);
	}

	@Override
	public PartyType type() {
		return PartyType.MERCHANT;
	}

	@Override
	public MerchantIdentity withDisplayName(String newDisplayName) {
		return new MerchantIdentity(id, externalReference, newDisplayName);
	}
}
