package com.routemind.business.application.order;

import com.routemind.business.domain.order.OrderStatus;
import java.util.UUID;

public interface FulfillmentAssignmentCoordinator {

	void beforeTransition(UUID orderId, OrderStatus current, OrderStatus target);
}
