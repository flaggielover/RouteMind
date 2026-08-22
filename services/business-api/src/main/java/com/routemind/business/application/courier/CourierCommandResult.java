package com.routemind.business.application.courier;

import java.util.UUID;

public record CourierCommandResult(UUID courierId, String status, long version, boolean replayed) {
}
