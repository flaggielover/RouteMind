package com.routemind.business.infrastructure.persistence.order;

import com.routemind.business.domain.order.Order;
import com.routemind.business.domain.order.OrderId;
import com.routemind.business.domain.order.OrderStatus;
import com.routemind.business.domain.order.OrderTransition;
import com.routemind.business.infrastructure.persistence.TenantScopedEntity;
import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.OneToMany;
import jakarta.persistence.OrderBy;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Entity
@Table(name = "orders", schema = "routemind")
class OrderEntity extends TenantScopedEntity {

	@Id
	private UUID id;

	@Enumerated(EnumType.STRING)
	@Column(nullable = false, length = 32)
	private OrderStatus status;

	@Column(name = "created_at", nullable = false)
	private Instant createdAt;

	@Column(name = "updated_at", nullable = false)
	private Instant updatedAt;

	@Version
	@Column(nullable = false)
	private Long version;

	@OneToMany(mappedBy = "order", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.EAGER)
	@OrderBy("sequenceNumber ASC")
	private List<OrderTransitionEntity> transitions = new ArrayList<>();

	protected OrderEntity() {
	}

	private OrderEntity(Order order, UUID tenantId) {
		assignTenant(tenantId);
		id = order.id().value();
		apply(order);
	}

	static OrderEntity from(Order order, UUID tenantId) {
		return new OrderEntity(order, tenantId);
	}

	void apply(Order order) {
		if (id != null && !id.equals(order.id().value())) {
			throw new IllegalArgumentException("order identity cannot change");
		}
		id = order.id().value();
	status = order.status();
	createdAt = order.createdAt();
	updatedAt = order.updatedAt();
	for (int index = 0; index < order.transitions().size(); index++) {
		OrderTransition transition = order.transitions().get(index);
		if (index < transitions.size()) {
			transitions.get(index).apply(transition);
		}
		else {
			transitions.add(OrderTransitionEntity.from(this, transition, tenantId()));
		}
	}
	while (transitions.size() > order.transitions().size()) {
		transitions.remove(transitions.size() - 1);
	}
	}

	long persistedVersion() {
		return version == null ? 0 : version;
	}

	Order toDomain() {
		return new Order(new OrderId(id), status, persistedVersion(), createdAt, updatedAt,
				transitions.stream().map(OrderTransitionEntity::toDomain).toList());
	}
}
