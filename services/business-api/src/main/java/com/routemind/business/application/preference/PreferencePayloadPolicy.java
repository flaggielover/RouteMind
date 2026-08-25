package com.routemind.business.application.preference;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.time.LocalTime;
import java.time.ZoneId;
import java.util.Locale;
import java.util.Set;
import org.springframework.stereotype.Component;

@Component
public final class PreferencePayloadPolicy {

	private static final Set<String> THEMES = Set.of("system", "light", "dark");
	private static final Set<String> CONTRASTS = Set.of("system", "standard", "high");
	private static final Set<String> MOTION = Set.of("system", "reduce", "no-preference");
	private static final Set<String> ANNOUNCEMENTS = Set.of("off", "polite", "assertive");
	private final ObjectMapper mapper;

	public PreferencePayloadPolicy(ObjectMapper mapper) {
		this.mapper = mapper;
	}

	public String canonicalize(PreferenceNamespace namespace, JsonNode raw) {
		if (raw == null || !raw.isObject()) throw invalid();
		ObjectNode value = switch (namespace) {
			case ACCESSIBILITY -> accessibility(raw);
			case LOCALE -> locale(raw);
			case NOTIFICATIONS -> notifications(raw);
			case QUIET_HOURS -> quietHours(raw);
		};
		try {
			return mapper.writeValueAsString(value);
		}
		catch (JsonProcessingException exception) {
			throw new IllegalArgumentException("preference_value_invalid", exception);
		}
	}

	public String defaults(PreferenceNamespace namespace) {
		ObjectNode value = mapper.createObjectNode();
		switch (namespace) {
			case ACCESSIBILITY -> {
				value.put("theme", "system");
				value.put("contrast", "system");
				value.put("reducedMotion", "system");
				value.put("textScale", 1.0);
				value.put("screenReaderAnnouncements", "polite");
				value.put("visibleFocus", true);
				value.put("colorOnlyStatus", false);
			}
			case LOCALE -> {
				value.put("locale", "en-US");
				value.put("timeZone", "UTC");
			}
			case NOTIFICATIONS -> {
				value.put("in_app", true);
				value.put("email", false);
				value.put("sms", false);
				value.put("push", false);
			}
			case QUIET_HOURS -> {
				value.put("enabled", false);
				value.put("startLocal", "22:00");
				value.put("endLocal", "07:00");
			}
		}
		try {
			return mapper.writeValueAsString(value);
		}
		catch (JsonProcessingException exception) {
			throw new IllegalStateException("preference defaults are not serializable", exception);
		}
	}

	private ObjectNode accessibility(JsonNode raw) {
		exact(raw, "theme", "contrast", "reducedMotion", "textScale", "screenReaderAnnouncements",
				"visibleFocus", "colorOnlyStatus");
		ObjectNode value = mapper.createObjectNode();
		value.put("theme", choice(raw, "theme", THEMES));
		value.put("contrast", choice(raw, "contrast", CONTRASTS));
		value.put("reducedMotion", choice(raw, "reducedMotion", MOTION));
		JsonNode scale = raw.get("textScale");
		if (!scale.isNumber() || scale.doubleValue() < 0.8 || scale.doubleValue() > 2.0) throw invalid();
		value.put("textScale", scale.doubleValue());
		value.put("screenReaderAnnouncements", choice(raw, "screenReaderAnnouncements", ANNOUNCEMENTS));
		value.put("visibleFocus", bool(raw, "visibleFocus"));
		value.put("colorOnlyStatus", bool(raw, "colorOnlyStatus"));
		return value;
	}

	private ObjectNode locale(JsonNode raw) {
		exact(raw, "locale", "timeZone");
		String locale = text(raw, "locale", 35);
		if (Locale.forLanguageTag(locale).getLanguage().isBlank()) throw invalid();
		String timeZone = text(raw, "timeZone", 64);
		try {
			ZoneId.of(timeZone);
		}
		catch (RuntimeException exception) {
			throw invalid();
		}
		ObjectNode value = mapper.createObjectNode();
		value.put("locale", locale);
		value.put("timeZone", timeZone);
		return value;
	}

	private ObjectNode notifications(JsonNode raw) {
		exact(raw, "in_app", "email", "sms", "push");
		ObjectNode value = mapper.createObjectNode();
		value.put("in_app", bool(raw, "in_app"));
		value.put("email", bool(raw, "email"));
		value.put("sms", bool(raw, "sms"));
		value.put("push", bool(raw, "push"));
		return value;
	}

	private ObjectNode quietHours(JsonNode raw) {
		exact(raw, "enabled", "startLocal", "endLocal");
		String start = time(raw, "startLocal");
		String end = time(raw, "endLocal");
		ObjectNode value = mapper.createObjectNode();
		value.put("enabled", bool(raw, "enabled"));
		value.put("startLocal", start);
		value.put("endLocal", end);
		return value;
	}

	private static void exact(JsonNode raw, String... expected) {
		Set<String> fields = new java.util.HashSet<>();
		raw.fieldNames().forEachRemaining(fields::add);
		if (!fields.equals(Set.of(expected))) throw invalid();
	}

	private static String choice(JsonNode raw, String field, Set<String> choices) {
		String value = text(raw, field, 32);
		if (!choices.contains(value)) throw invalid();
		return value;
	}

	private static String text(JsonNode raw, String field, int max) {
		JsonNode node = raw.get(field);
		if (node == null || !node.isTextual() || node.textValue().isBlank() || node.textValue().length() > max
				|| node.textValue().chars().anyMatch(Character::isISOControl)) throw invalid();
		return node.textValue();
	}

	private static boolean bool(JsonNode raw, String field) {
		JsonNode node = raw.get(field);
		if (node == null || !node.isBoolean()) throw invalid();
		return node.booleanValue();
	}

	private static String time(JsonNode raw, String field) {
		String value = text(raw, field, 5);
		try {
			LocalTime parsed = LocalTime.parse(value);
			if (parsed.getSecond() != 0 || parsed.getNano() != 0) throw invalid();
			return value;
		}
		catch (RuntimeException exception) {
			throw invalid();
		}
	}

	private static IllegalArgumentException invalid() {
		return new IllegalArgumentException("preference_value_invalid");
	}
}
