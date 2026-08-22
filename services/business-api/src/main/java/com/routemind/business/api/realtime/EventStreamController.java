package com.routemind.business.api.realtime;

import com.routemind.business.application.realtime.EventStreamEntry;
import com.routemind.business.application.realtime.EventStreamService;
import com.routemind.business.application.realtime.EventStreamStaleException;
import com.routemind.business.domain.event.EventEnvelope;
import java.io.IOException;
import java.util.List;
import java.util.regex.Pattern;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@RestController
@RequestMapping("/api/v1/events")
@CrossOrigin(origins = { "http://localhost:4173", "http://127.0.0.1:4173" })
public final class EventStreamController {

	private static final Logger LOGGER = LoggerFactory.getLogger(EventStreamController.class);
	private static final Pattern CURSOR = Pattern.compile("^(0|[1-9][0-9]*)$");
	private static final long EMITTER_TIMEOUT_MILLIS = 5_000;

	private final EventStreamService service;

	public EventStreamController(EventStreamService service) {
		this.service = service;
	}

	@GetMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
	public SseEmitter stream(
			@RequestHeader(name = "Last-Event-ID", required = false) String lastEventId,
			@RequestParam(name = "after", defaultValue = "0") String after) {
		long cursor = parseCursor(lastEventId == null || lastEventId.isBlank() ? after : lastEventId);
		final List<EventStreamEntry> entries;
		try {
			entries = service.after(cursor, EventStreamService.MAX_BATCH_SIZE);
		}
		catch (EventStreamStaleException exception) {
			throw new ResponseStatusException(HttpStatus.CONFLICT, exception.getMessage(), exception);
		}
		SseEmitter emitter = new SseEmitter(EMITTER_TIMEOUT_MILLIS);
		emitter.onTimeout(() -> {
			LOGGER.warn("event_stream_subscriber_lost reason=timeout cursor={}", cursor);
			emitter.complete();
		});
		emitter.onError(error -> LOGGER.warn("event_stream_subscriber_lost reason=error cursor={}", cursor, error));
		try {
			for (EventStreamEntry entry : entries) {
				emitter.send(SseEmitter.event()
						.id(Long.toString(entry.cursor()))
						.name(entry.event().eventType())
						.data(EventStreamItem.from(entry)));
			}
			emitter.complete();
		}
		catch (IOException exception) {
			LOGGER.warn("event_stream_subscriber_lost reason=send_failure cursor={}", cursor, exception);
			emitter.completeWithError(exception);
		}
		return emitter;
	}

	private static long parseCursor(String value) {
		if (value == null || !CURSOR.matcher(value).matches()) {
			throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "event stream cursor must be decimal");
		}
		try {
			return Long.parseLong(value);
		}
		catch (NumberFormatException exception) {
			throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "event stream cursor is too large", exception);
		}
	}

	public record EventStreamItem(String schemaVersion, String cursor, EventEnvelope event,
			boolean replay, boolean stale, String staleReason) {

		static EventStreamItem from(EventStreamEntry entry) {
			return new EventStreamItem("v1", Long.toString(entry.cursor()), entry.event(), false, false, null);
		}
	}
}
