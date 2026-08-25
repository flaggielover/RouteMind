package com.routemind.business.api.preference;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.routemind.business.application.preference.PreferenceAccessDeniedException;
import com.routemind.business.application.preference.PreferenceConflictException;
import com.routemind.business.application.preference.PreferenceDocument;
import com.routemind.business.application.preference.PreferenceNamespace;
import com.routemind.business.application.preference.PreferenceIdentityResolver;
import com.routemind.business.application.preference.UserPreferenceService;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.CacheControl;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MissingRequestHeaderException;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/preferences")
@CrossOrigin(origins = { "http://localhost:4173", "http://127.0.0.1:4173" })
public final class UserPreferenceController {

	private final UserPreferenceService service;
	private final PreferenceIdentityResolver identities;
	private final ObjectMapper mapper;

	public UserPreferenceController(UserPreferenceService service, PreferenceIdentityResolver identities,
			ObjectMapper mapper) {
		this.service = service;
		this.identities = identities;
		this.mapper = mapper;
	}

	@GetMapping("/{namespace}")
	public ResponseEntity<PreferenceResponse> read(@PathVariable String namespace,
			@RequestHeader("X-Actor") String actor) {
		PreferenceDocument document = service.read(identities.resolve(actor), PreferenceNamespace.parse(namespace));
		return response(HttpStatus.OK, document);
	}

	@PutMapping("/{namespace}")
	public ResponseEntity<PreferenceResponse> write(@PathVariable String namespace,
			@RequestHeader("X-Actor") String actor, @RequestHeader("Idempotency-Key") String idempotencyKey,
			@RequestBody PreferenceWriteRequest request) {
		if (request == null || request.expectedVersion() == null || request.values() == null) {
			throw new IllegalArgumentException("preference_request_invalid");
		}
		PreferenceDocument document = service.write(identities.resolve(actor), PreferenceNamespace.parse(namespace),
				mapper.valueToTree(request.values()), request.expectedVersion(), idempotencyKey);
		HttpStatus status = document.version() == 1 && !document.replayed() ? HttpStatus.CREATED : HttpStatus.OK;
		return response(status, document);
	}

	@ExceptionHandler(PreferenceAccessDeniedException.class)
	ResponseEntity<ErrorResponse> forbidden(PreferenceAccessDeniedException exception) {
		return ResponseEntity.status(HttpStatus.FORBIDDEN).body(new ErrorResponse(exception.getMessage()));
	}

	@ExceptionHandler(PreferenceConflictException.class)
	ResponseEntity<ErrorResponse> conflict(PreferenceConflictException exception) {
		return ResponseEntity.status(HttpStatus.CONFLICT).body(new ErrorResponse(exception.getMessage()));
	}

	@ExceptionHandler(DataIntegrityViolationException.class)
	ResponseEntity<ErrorResponse> concurrentWrite() {
		return ResponseEntity.status(HttpStatus.CONFLICT).body(new ErrorResponse("preference_concurrent_write"));
	}

	@ExceptionHandler({ IllegalArgumentException.class, MissingRequestHeaderException.class })
	ResponseEntity<ErrorResponse> invalid(Exception exception) {
		String code = exception instanceof IllegalArgumentException && exception.getMessage() != null
				? exception.getMessage() : "preference_request_invalid";
		return ResponseEntity.badRequest().body(new ErrorResponse(code));
	}

	private ResponseEntity<PreferenceResponse> response(HttpStatus status, PreferenceDocument document) {
		try {
				PreferenceResponse body = new PreferenceResponse(document.namespace().id(), mapper.readValue(document.valueJson(), Map.class),
					document.version(), document.persisted(), document.replayed(), document.createdAt(), document.updatedAt());
			return ResponseEntity.status(status).cacheControl(CacheControl.noStore())
					.eTag("\"" + document.version() + "\"").body(body);
		}
		catch (JsonProcessingException exception) {
			throw new IllegalStateException("stored preference JSON is invalid", exception);
		}
	}

	public record PreferenceWriteRequest(Long expectedVersion, Map<String, Object> values) {
	}

	public record PreferenceResponse(String namespace, Map<String, Object> values, long version, boolean persisted,
			boolean replayed, java.time.Instant createdAt, java.time.Instant updatedAt) {
	}

	public record ErrorResponse(String code) {
	}
}
