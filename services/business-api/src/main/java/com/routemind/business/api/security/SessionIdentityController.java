package com.routemind.business.api.security;

import com.routemind.business.application.security.CurrentSessionIdentity;
import com.routemind.business.application.security.SessionIdentity;
import java.time.Instant;
import java.util.List;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/v1/session")
@CrossOrigin(origins = { "http://localhost:4173", "http://127.0.0.1:4173" })
@ConditionalOnProperty(name = "routemind.security.oidc.enabled", havingValue = "true")
public final class SessionIdentityController {

	private final CurrentSessionIdentity identities;

	public SessionIdentityController(CurrentSessionIdentity identities) {
		this.identities = identities;
	}

	@GetMapping
	public SessionIdentityResponse current() {
		SessionIdentity identity = identities.current().orElseThrow(
				() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED, "verified JWT identity is required"));
		return new SessionIdentityResponse("v1", identity.subject(), identity.tenantId().value().toString(),
				identity.roles().stream().sorted().toList(), identity.expiresAt());
	}

	public record SessionIdentityResponse(String schemaVersion, String subject, String tenantId,
			List<String> roles, Instant expiresAt) {
	}
}
