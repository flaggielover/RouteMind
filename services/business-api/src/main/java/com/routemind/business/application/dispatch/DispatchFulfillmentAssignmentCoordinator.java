package com.routemind.business.application.dispatch;

import com.routemind.business.application.order.FulfillmentAssignmentCoordinator;
import com.routemind.business.domain.order.OrderStatus;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;
import org.springframework.stereotype.Service;

@Service
public final class DispatchFulfillmentAssignmentCoordinator implements FulfillmentAssignmentCoordinator {

	private static final Set<OrderStatus> RELEASE_TARGETS = Set.of(OrderStatus.DELIVERED,
			OrderStatus.ASSIGNMENT_TIMED_OUT, OrderStatus.ASSIGNMENT_REJECTED,
			OrderStatus.COMPENSATING);

	private final DispatchAssignmentLeaseService leases;

	public DispatchFulfillmentAssignmentCoordinator(DispatchAssignmentLeaseService leases) {
		this.leases = leases;
	}

	@Override
	public void beforeTransition(UUID orderId, OrderStatus current, OrderStatus target) {
		if (RELEASE_TARGETS.contains(target)) {
			leases.releaseCommittedForOrder(orderId,
					"fulfillment_" + current.name().toLowerCase(Locale.ROOT) + "_to_"
							+ target.name().toLowerCase(Locale.ROOT));
		}
	}
}
