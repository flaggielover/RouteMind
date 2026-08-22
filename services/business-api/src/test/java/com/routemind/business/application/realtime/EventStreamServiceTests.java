package com.routemind.business.application.realtime;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.routemind.business.domain.event.EventEnvelope;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class EventStreamServiceTests {

	@Test
	void returnsEntriesStrictlyAfterCursorAndHonorsRequestedLimit() {
		EventStreamService service = new EventStreamService(repositoryWithEntries(3, 4, 5));

		assertThat(service.after(3, 1).stream().map(EventStreamEntry::cursor).toList()).containsExactly(4L);
		assertThat(service.after(0, 64).stream().map(EventStreamEntry::cursor).toList()).containsExactly(3L, 4L, 5L);
	}

	@Test
	void rejectsCursorOutsideRetainedWindow() {
		EventStreamService service = new EventStreamService(repositoryWithEntries(3, 4, 5));

		assertThatThrownBy(() -> service.after(1, 64))
				.isInstanceOf(EventStreamStaleException.class)
				.hasMessageContaining("outside retention");
	}

	@Test
	void rejectsInvalidCursorAndBatchBounds() {
		EventStreamService service = new EventStreamService(repositoryWithEntries(3, 4, 5));

		assertThatThrownBy(() -> service.after(-1, 1)).isInstanceOf(IllegalArgumentException.class);
		assertThatThrownBy(() -> service.after(0, 0)).isInstanceOf(IllegalArgumentException.class);
		assertThatThrownBy(() -> service.after(0, EventStreamService.MAX_BATCH_SIZE + 1))
				.isInstanceOf(IllegalArgumentException.class);
	}

	private static EventStreamRepository repositoryWithEntries(long... cursors) {
		List<EventStreamEntry> entries = java.util.Arrays.stream(cursors)
				.mapToObj(cursor -> new EventStreamEntry(cursor, event(cursor)))
				.toList();
		EventStreamPage page = new EventStreamPage(entries.get(0).cursor(), entries.get(entries.size() - 1).cursor(), entries);
		return limit -> {
			assertThat(limit).isEqualTo(EventStreamService.MAX_BATCH_SIZE);
			return page;
		};
	}

	private static EventEnvelope event(long cursor) {
		return new EventEnvelope("1.0", UUID.randomUUID(), "order.status.changed", Instant.parse("2026-01-01T00:00:00Z"),
				"business-api", UUID.randomUUID(), cursor, UUID.randomUUID(), null,
				"0123456789abcdef0123456789abcdef", Map.of("cursor", cursor));
	}
}
