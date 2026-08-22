package com.routemind.business.application.order;

import com.routemind.business.domain.order.Order;
import com.routemind.business.domain.order.OrderId;
import java.util.List;
import java.util.Optional;

public interface OrderRepository {

	Order save(Order order);

	Optional<Order> findById(OrderId id);

	List<Order> findAll();
}
