package com.routemind.business.infrastructure.persistence.order;

import com.routemind.business.domain.order.OrderStatus;
import com.routemind.business.domain.order.OrderTransition;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "order_transitions", schema = "routemind")
class OrderTransitionEntity {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@ManyToOne(fetch = FetchType.LAZY, optional = false)
	@JoinColumn(name = "order_id", nullable = false)
	private OrderEntity order;

	@Column(name = "sequence_number", nullable = false)
	private long sequenceNumber;

	@Enumerated(EnumType.STRING)
	@Column(name = "from_status", nullable = false, length = 16)
	private OrderStatus from;

	@Enumerated(EnumType.STRING)
	@Column(name = "to_status", nullable = false, length = 16)
	private OrderStatus to;

	@Column(nullable = false, length = 64)
	private String actor;

	@Column(name = "occurred_at", nullable = false)
	private Instant occurredAt;

	protected OrderTransitionEntity() {
	}

	private OrderTransitionEntity(OrderEntity order, OrderTransition transition) {
		this.order = order;
		sequenceNumber = transition.sequenceNumber();
		from = transition.from();
		to = transition.to();
		actor = transition.actor();
		occurredAt = transition.occurredAt();
	}

	static OrderTransitionEntity from(OrderEntity order, OrderTransition transition) {
		return new OrderTransitionEntity(order, transition);
	}

	OrderTransition toDomain() {
		return new OrderTransition(sequenceNumber, from, to, actor, occurredAt);
	}
}
