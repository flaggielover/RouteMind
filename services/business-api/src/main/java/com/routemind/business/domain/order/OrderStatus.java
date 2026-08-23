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
	ASSIGNMENT_TIMED_OUT,
	ASSIGNMENT_REJECTED,
	REASSIGNMENT_PENDING,
	COMPENSATING,
	COMPENSATED,
	CANCELLED;

	boolean canTransitionTo(OrderStatus target) {
		return switch (this) {
			case CREATED -> target == CONFIRMED || target == CANCELLED;
			case CONFIRMED -> target == PREPARING || target == ASSIGNED || target == CANCELLED;
			case PREPARING -> target == READY_FOR_PICKUP || target == CANCELLED;
			case READY_FOR_PICKUP -> target == ASSIGNED || target == CANCELLED;
			case ASSIGNED -> target == ACCEPTED || target == ARRIVED || target == PICKED_UP
					|| target == ASSIGNMENT_TIMED_OUT || target == ASSIGNMENT_REJECTED
					|| target == COMPENSATING || target == CANCELLED;
			case ACCEPTED -> target == ARRIVED || target == PICKED_UP
					|| target == ASSIGNMENT_TIMED_OUT || target == COMPENSATING
					|| target == CANCELLED;
			case ARRIVED -> target == PICKED_UP || target == ASSIGNMENT_TIMED_OUT
					|| target == COMPENSATING || target == CANCELLED;
			case PICKED_UP -> target == DELIVERED;
			case ASSIGNMENT_TIMED_OUT, ASSIGNMENT_REJECTED -> target == REASSIGNMENT_PENDING
					|| target == COMPENSATING;
			case REASSIGNMENT_PENDING -> target == ASSIGNED || target == COMPENSATING;
			case COMPENSATING -> target == COMPENSATED;
			case COMPENSATED -> target == CANCELLED;
			case DELIVERED, CANCELLED -> false;
		};
	}
}
