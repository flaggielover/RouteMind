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
			case ASSIGNED -> "dispatch".equals(actor) && current == OrderStatus.CONFIRMED;
			case PICKED_UP -> "courier".equals(actor) && current == OrderStatus.ASSIGNED;
			case DELIVERED -> "courier".equals(actor) && current == OrderStatus.PICKED_UP;
		case CANCELLED -> ("customer".equals(actor) || "merchant".equals(actor)
					|| "dispatch".equals(actor)) && current != OrderStatus.DELIVERED;
			case CREATED -> false;
		};
		if (!allowed) {
			throw new OrderCommandAuthorizationException("actor_not_authorized");
		}
	}
}
