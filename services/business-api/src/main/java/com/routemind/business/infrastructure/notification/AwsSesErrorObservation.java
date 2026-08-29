package com.routemind.business.infrastructure.notification;

import java.time.Instant;
import java.util.Locale;
import java.util.Objects;
import java.util.regex.Pattern;
import software.amazon.awssdk.core.exception.SdkClientException;
import software.amazon.awssdk.awscore.exception.AwsServiceException;
import software.amazon.awssdk.services.ses.model.SesException;

/** Structured provider failure metadata. Raw exception messages and identifiers are never retained. */
public record AwsSesErrorObservation(String provider, String operation, String region,
		String exceptionClass, String serviceErrorCode, int httpStatus, RequestIdHandling requestId,
		Category normalizedCategory, String sanitizedProviderSemantic, boolean providerAcceptance,
		int requestCount, int retryCount, boolean fallbackUsed, Instant observedAt,
		SesRequestShapeAudit requestShape) {

	private static final Pattern SAFE_TOKEN = Pattern.compile("[A-Za-z0-9._-]{1,128}");

	public enum RequestIdHandling {
		ABSENT,
		PRESENT_REDACTED
	}

	public enum Category {
		AUTHORIZATION_REJECTED,
		RATE_LIMITED,
		PROVIDER_SERVER_FAILURE,
		PROVIDER_REQUEST_REJECTED,
		CLIENT_RUNTIME_FAILURE
	}

	public AwsSesErrorObservation {
		if (!"AWS_SES".equals(provider)) throw new IllegalArgumentException("provider is invalid");
		if (!"SendEmail".equals(operation)) throw new IllegalArgumentException("operation is invalid");
		if (region == null || !SAFE_TOKEN.matcher(region).matches()) {
			throw new IllegalArgumentException("region is invalid");
		}
		if (exceptionClass == null || !SAFE_TOKEN.matcher(exceptionClass).matches()) {
			throw new IllegalArgumentException("exceptionClass is invalid");
		}
		if (serviceErrorCode == null || !SAFE_TOKEN.matcher(serviceErrorCode).matches()) {
			throw new IllegalArgumentException("serviceErrorCode is invalid");
		}
		if (httpStatus < 0 || httpStatus > 599) throw new IllegalArgumentException("httpStatus is invalid");
		Objects.requireNonNull(requestId, "requestId");
		Objects.requireNonNull(normalizedCategory, "normalizedCategory");
		if (!normalizedCategory.name().equals(sanitizedProviderSemantic)) {
			throw new IllegalArgumentException("provider semantic must be normalized");
		}
		if (providerAcceptance) throw new IllegalArgumentException("error observation cannot claim acceptance");
		if (requestCount != 1) throw new IllegalArgumentException("SES error observation requires one request");
		if (retryCount < 0) throw new IllegalArgumentException("retryCount is invalid");
		if (fallbackUsed) throw new IllegalArgumentException("SES error observation cannot represent fallback");
		Objects.requireNonNull(observedAt, "observedAt");
		Objects.requireNonNull(requestShape, "requestShape");
	}

	public static AwsSesErrorObservation from(SesException exception, String region,
			SesRequestShapeAudit requestShape, Instant observedAt) {
		Objects.requireNonNull(exception, "exception");
		String errorCode = safeErrorCode(exception.awsErrorDetails() == null
				? null : exception.awsErrorDetails().errorCode());
		Category category = category(errorCode, exception.statusCode());
		return new AwsSesErrorObservation("AWS_SES", "SendEmail", region, "SesException", errorCode,
				exception.statusCode(), requestId(exception.requestId()), category, category.name(), false,
				1, 0, false, observedAt, requestShape);
	}

	public static AwsSesErrorObservation from(SdkClientException exception, String region,
			SesRequestShapeAudit requestShape, Instant observedAt) {
		Objects.requireNonNull(exception, "exception");
		Category category = Category.CLIENT_RUNTIME_FAILURE;
		return new AwsSesErrorObservation("AWS_SES", "SendEmail", region, "SdkClientException",
				"NOT_AVAILABLE", 0, RequestIdHandling.ABSENT, category, category.name(), false,
				1, 0, false, observedAt, requestShape);
	}

	/**
	 * Captures the common AWS service error shape without retaining raw messages.
	 * This is useful when a future SDK operation exposes a service exception that
	 * is not modeled as SesException by the generated client.
	 */
	public static AwsSesErrorObservation from(AwsServiceException exception, String region,
			SesRequestShapeAudit requestShape, Instant observedAt) {
		Objects.requireNonNull(exception, "exception");
		String errorCode = safeErrorCode(exception.awsErrorDetails() == null
				? null : exception.awsErrorDetails().errorCode());
		Category category = category(errorCode, exception.statusCode());
		return new AwsSesErrorObservation("AWS_SES", "SendEmail", region, exception.getClass().getSimpleName(),
				errorCode, exception.statusCode(), requestId(exception.requestId()), category, category.name(), false,
				1, 0, false, observedAt, requestShape);
	}

	private static String safeErrorCode(String value) {
		return value != null && SAFE_TOKEN.matcher(value).matches() ? value : "UNAVAILABLE_OR_UNSAFE";
	}

	private static RequestIdHandling requestId(String value) {
		return value == null || value.isBlank() ? RequestIdHandling.ABSENT : RequestIdHandling.PRESENT_REDACTED;
	}

	private static Category category(String errorCode, int status) {
		String normalized = errorCode.toLowerCase(Locale.ROOT);
		if (status == 401 || status == 403 || normalized.contains("accessdenied")
				|| normalized.contains("unauthorized")) {
			return Category.AUTHORIZATION_REJECTED;
		}
		if (status == 429 || normalized.contains("throttl") || normalized.contains("limitexceeded")) {
			return Category.RATE_LIMITED;
		}
		if (status >= 500) return Category.PROVIDER_SERVER_FAILURE;
		return Category.PROVIDER_REQUEST_REJECTED;
	}
}
