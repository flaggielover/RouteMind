package com.routemind.business.application.dispatch;

import com.routemind.business.domain.dispatch.DispatchDecisionLedger;
import java.util.Optional;

public interface DispatchDecisionLedgerRepository {

    DispatchDecisionLedger save(DispatchDecisionLedger ledger);

    Optional<DispatchDecisionLedger> findByDecisionId(String decisionId);
}
