package com.routemind.business.application.order;

import com.routemind.business.domain.order.OrderStatus;

final class OrderCommandAuthorization {

	private OrderCommandAuthorization() {
	}

	static void requireCreate(String actor) {
		if (!"customer".equals(actor) && !"merchant".equals(actor)) {
			throw new OrderCommandAuthorizationException("actor_not_authorized");
		}
	}

	static void requireTransition(String actor, OrderStatus current, OrderStatus target) {
		boolean allowed = switch (target) {
			case CONFIRMED -> ("customer".equals(actor) || "merchant".equals(actor))
					&& current == OrderStatus.CREATED;
			case PREPARING -> "merchant".equals(actor) && current == OrderStatus.CONFIRMED;
			case READY_FOR_PICKUP -> "merchant".equals(actor) && current == OrderStatus.PREPARING;
			case ASSIGNED -> "dispatch".equals(actor)
					&& (current == OrderStatus.CONFIRMED || current == OrderStatus.READY_FOR_PICKUP
							|| current == OrderStatus.REASSIGNMENT_PENDING);
			case ACCEPTED -> "courier".equals(actor) && current == OrderStatus.ASSIGNED;
			case ARRIVED -> "courier".equals(actor)
					&& (current == OrderStatus.ASSIGNED || current == OrderStatus.ACCEPTED);
			case PICKED_UP -> "courier".equals(actor)
					&& (current == OrderStatus.ASSIGNED || current == OrderStatus.ACCEPTED
							|| current == OrderStatus.ARRIVED);
			case DELIVERED -> "courier".equals(actor) && current == OrderStatus.PICKED_UP;
			case ASSIGNMENT_TIMED_OUT -> ("system".equals(actor) || "dispatch".equals(actor))
					&& (current == OrderStatus.ASSIGNED || current == OrderStatus.ACCEPTED
							|| current == OrderStatus.ARRIVED);
			case ASSIGNMENT_REJECTED -> "courier".equals(actor) && current == OrderStatus.ASSIGNED;
			case REASSIGNMENT_PENDING -> "dispatch".equals(actor)
					&& (current == OrderStatus.ASSIGNMENT_TIMED_OUT
							|| current == OrderStatus.ASSIGNMENT_REJECTED);
			case COMPENSATING -> ("customer".equals(actor) || "merchant".equals(actor)
					|| "dispatch".equals(actor) || "system".equals(actor))
					&& (current == OrderStatus.ASSIGNED || current == OrderStatus.ACCEPTED
							|| current == OrderStatus.ARRIVED
							|| current == OrderStatus.ASSIGNMENT_TIMED_OUT
							|| current == OrderStatus.ASSIGNMENT_REJECTED
							|| current == OrderStatus.REASSIGNMENT_PENDING);
			case COMPENSATED -> "system".equals(actor) && current == OrderStatus.COMPENSATING;
			case CANCELLED -> current == OrderStatus.COMPENSATED
					? "system".equals(actor)
					: ("customer".equals(actor) || "merchant".equals(actor)
							|| "dispatch".equals(actor))
							&& (current == OrderStatus.CREATED || current == OrderStatus.CONFIRMED
									|| current == OrderStatus.PREPARING
									|| current == OrderStatus.READY_FOR_PICKUP
									|| current == OrderStatus.ASSIGNED
									|| current == OrderStatus.ACCEPTED
									|| current == OrderStatus.ARRIVED
									|| current == OrderStatus.ASSIGNMENT_TIMED_OUT
									|| current == OrderStatus.ASSIGNMENT_REJECTED
									|| current == OrderStatus.REASSIGNMENT_PENDING);
			case CREATED -> false;
		};
		if (!allowed) {
			throw new OrderCommandAuthorizationException("actor_not_authorized");
		}
	}
}
