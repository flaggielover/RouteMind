package com.routemind.business.application.notification;

import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class NotificationTemplateRenderer {

	private static final Pattern PLACEHOLDER = Pattern.compile("\\{\\{([a-z][a-z0-9_]*)}}");

	public NotificationRequest render(NotificationCommand command, NotificationTemplate template) {
		Objects.requireNonNull(command, "command");
		Objects.requireNonNull(template, "template");
		if (command.channel() != template.channel() || !command.templateId().equals(template.id())) {
			throw new IllegalArgumentException("notification template does not match command");
		}
		NotificationPrivacyPolicy.validate(command.templateData());
		String subject = render(template.subjectTemplate(), command.templateData(), template.allowedVariables());
		String body = render(template.bodyTemplate(), command.templateData(), template.allowedVariables());
		return new NotificationRequest(command.notificationId(), command.tenantId(), command.correlationId(),
				command.idempotencyKey(), command.channel(), command.recipient(), command.sender(), command.templateId(),
				subject, body, 1, UUID.nameUUIDFromBytes((command.idempotencyKey() + ":1")
					.getBytes(StandardCharsets.UTF_8)),
				command.requestedAt(), Map.of("trace_id", command.traceId(), "privacy_boundary", NotificationPrivacyPolicy.REQUIRED_BOUNDARY));
	}

	private static String render(String template, Map<String, String> data, java.util.Set<String> allowed) {
		Matcher matcher = PLACEHOLDER.matcher(template);
		StringBuffer rendered = new StringBuffer();
		while (matcher.find()) {
			String key = matcher.group(1);
			if (!allowed.contains(key) || !data.containsKey(key)) {
				throw new IllegalArgumentException("template variable is not declared");
			}
			matcher.appendReplacement(rendered, Matcher.quoteReplacement(data.get(key)));
		}
		matcher.appendTail(rendered);
		if (rendered.toString().contains("{{")) throw new IllegalArgumentException("template has unresolved variable");
		return rendered.toString();
	}
}
