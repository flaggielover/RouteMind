package com.routemind.business.domain.party;

public sealed interface PartyIdentity permits CustomerIdentity, MerchantIdentity, CourierIdentity {

	PartyId id();

	String externalReference();

	String displayName();

	PartyType type();

	PartyIdentity withDisplayName(String displayName);
}
