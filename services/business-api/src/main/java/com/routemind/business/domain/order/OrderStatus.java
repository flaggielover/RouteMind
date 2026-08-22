package com.routemind.business.domain.order;

public enum OrderStatus {
	CREATED,
	CONFIRMED,
	PREPARING,
	READY_FOR_PICKUP,
	ASSIGNED,
	ACCEPTED,
	ARRIVED,
	PICKED_UP,
	DELIVERED,
	CANCELLED;

	boolean canTransitionTo(OrderStatus target) {
		return switch (this) {
			case CREATED -> target == CONFIRMED || target == CANCELLED;
			case CONFIRMED -> target == PREPARING || target == ASSIGNED || target == CANCELLED;
			case PREPARING -> target == READY_FOR_PICKUP || target == CANCELLED;
			case READY_FOR_PICKUP -> target == ASSIGNED || target == CANCELLED;
			case ASSIGNED -> target == ACCEPTED || target == ARRIVED || target == PICKED_UP || target == CANCELLED;
			case ACCEPTED -> target == ARRIVED || target == PICKED_UP || target == CANCELLED;
			case ARRIVED -> target == PICKED_UP || target == CANCELLED;
			case PICKED_UP -> target == DELIVERED;
			case DELIVERED, CANCELLED -> false;
		};
	}
}
