package com.routemind.business.application.party;

import com.routemind.business.domain.party.Party;
import com.routemind.business.domain.party.PartyId;
import java.util.Optional;

public interface PartyRepository {

	Party save(Party party);

	Optional<Party> findById(PartyId id);
}
