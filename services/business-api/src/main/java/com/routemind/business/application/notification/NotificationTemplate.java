package com.routemind.business.application.notification;

import java.util.Set;

public record NotificationTemplate(String id, NotificationChannel channel, String subjectTemplate,
		String bodyTemplate, Set<String> allowedVariables) {

	public NotificationTemplate {
		if (id == null || id.isBlank()) throw new IllegalArgumentException("template id is blank");
		if (channel == null) throw new IllegalArgumentException("template channel is required");
		if (subjectTemplate == null || subjectTemplate.isBlank()) throw new IllegalArgumentException("subject template is blank");
		if (bodyTemplate == null || bodyTemplate.isBlank()) throw new IllegalArgumentException("body template is blank");
		allowedVariables = Set.copyOf(allowedVariables == null ? Set.of() : allowedVariables);
	}
}
