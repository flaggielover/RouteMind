package com.routemind.business.domain.courier;

import java.util.UUID;

public record NearbyCourier(UUID courierId, double distanceKilometers) {
}
