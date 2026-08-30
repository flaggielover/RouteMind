package com.routemind.business.application.operations;

import com.routemind.business.application.courier.CourierLocationStore;
import com.routemind.business.application.dispatch.DispatchDecisionLedgerRepository;
import com.routemind.business.application.order.OrderRepository;
import com.routemind.business.application.party.PartyRepository;
import java.time.Clock;
import java.time.Instant;
import java.util.Objects;
import java.util.Optional;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class OperationsSnapshotService {

	private final OrderRepository orders;
	private final PartyRepository parties;
	private final CourierLocationStore courierLocations;
	private final DispatchDecisionLedgerRepository ledgers;
	private final Clock clock;

	public OperationsSnapshotService(OrderRepository orders, PartyRepository parties,
			CourierLocationStore courierLocations, DispatchDecisionLedgerRepository ledgers, Clock clock) {
		this.orders = Objects.requireNonNull(orders, "orders");
		this.parties = Objects.requireNonNull(parties, "parties");
		this.courierLocations = Objects.requireNonNull(courierLocations, "courierLocations");
		this.ledgers = Objects.requireNonNull(ledgers, "ledgers");
		this.clock = Objects.requireNonNull(clock, "clock");
	}

	@Transactional(readOnly = true)
	public OperationsSnapshot read() {
		var locations = courierLocations.findAll();
		var locationSummaries = locations.stream()
				.map(location -> new OperationsSnapshot.CourierLocationSummary(location.courierId(),
						location.point().latitude(), location.point().longitude(), location.sequence(),
						location.observedAt(), location.ingestedAt(), location.online()))
				.toList();
		var locationsByCourier = locationSummaries.stream()
				.collect(Collectors.toUnmodifiableMap(OperationsSnapshot.CourierLocationSummary::courierId,
						Function.identity(), (first, ignored) -> first));
		var ledgersByOrder = ledgers.findAll().stream()
				.collect(Collectors.toUnmodifiableMap(com.routemind.business.domain.dispatch.DispatchDecisionLedger::orderId,
						Function.identity(), (first, ignored) -> first));
		var assembler = new OperationsOrderReadModelAssembler(clock);
		return new OperationsSnapshot(Instant.now(clock),
				orders.findAll().stream()
						.map(order -> new OperationsSnapshot.OrderSummary(order.id().value(), order.status().name(),
								order.version(), order.createdAt(), order.updatedAt(),
								assemble(assembler, order.id().value(), order.status().name(), order.updatedAt(),
										ledgersByOrder, locationsByCourier))
						)
						.toList(),
				parties.findAll().stream()
						.map(party -> new OperationsSnapshot.PartySummary(party.id().value(), party.identity().type().name(),
								party.identity().displayName(), party.status().name()))
						.toList(),
				locationSummaries);
	}

	private OperationsOrderReadModel assemble(OperationsOrderReadModelAssembler assembler,
			java.util.UUID orderId, String status, Instant updatedAt,
			java.util.Map<java.util.UUID, com.routemind.business.domain.dispatch.DispatchDecisionLedger> ledgersByOrder,
			java.util.Map<java.util.UUID, OperationsSnapshot.CourierLocationSummary> locationsByCourier) {
		var ledger = ledgersByOrder.get(orderId);
		return assembler.assemble(orderId, status, updatedAt, Optional.ofNullable(ledger),
				ledger == null ? Optional.empty() : Optional.ofNullable(locationsByCourier.get(ledger.courierId())));
	}
}
