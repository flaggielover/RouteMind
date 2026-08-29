package com.routemind.business.infrastructure.notification;

import com.routemind.business.application.notification.NotificationRequest;
import java.util.Objects;
import software.amazon.awssdk.services.ses.model.SendEmailRequest;

/** Offline audit of the exact production request builder; no client or transport is involved. */
public record SesRuntimeContextAudit(RuntimeClassification runtimeClassification,
		HistoricalClassification historicalClassification, ConfigurationSource configurationSource,
		SesEndpointValueAudit sender, SesEndpointValueAudit recipient, SesRequestShapeAudit requestShape,
		boolean requestSourceMatchesNormalizedSender, boolean requestRecipientMatchesNormalizedRecipient,
		boolean endpointOverridePresent, boolean regionOverridePresent, RetryBehavior retryBehavior) {

	public enum RuntimeClassification {
		RUNTIME_CONTEXT_MATCH_CONFIRMED,
		RUNTIME_CONTEXT_MISMATCH_FOUND,
		COMPARISON_INPUT_UNAVAILABLE
	}

	public enum HistoricalClassification {
		HISTORICAL_CONTEXT_NOT_RECONSTRUCTABLE
	}

	public enum ConfigurationSource {
		PROCESS_ENVIRONMENT,
		SPRING_BOUND_PROPERTY,
		SYNTHETIC_TEST_FIXTURE
	}

	public enum RetryBehavior {
		AWS_SDK_RETRIES_DISABLED_APPLICATION_BOUNDED
	}

	public static SesRuntimeContextAudit inspect(String rawSender, String rawRecipient,
			String approvedSender, String approvedRecipient, NotificationRequest request,
			NotificationSesProperties properties, ConfigurationSource configurationSource,
			AwsSesRequestFactory requestFactory) {
		Objects.requireNonNull(request, "request");
		Objects.requireNonNull(properties, "properties");
		Objects.requireNonNull(configurationSource, "configurationSource");
		SendEmailRequest sdkRequest = Objects.requireNonNull(requestFactory, "requestFactory")
				.create(request, properties);
		SesEndpointValueAudit senderAudit = SesEndpointValueAudit.inspect(rawSender, properties.sender(),
				approvedSender);
		SesEndpointValueAudit recipientAudit = SesEndpointValueAudit.inspect(rawRecipient,
				properties.syntheticRecipient(), approvedRecipient);
		SesRequestShapeAudit shape = SesRequestShapeAudit.inspect(sdkRequest);
		boolean sourceMatches = sdkRequest.source().equals(properties.sender());
		boolean recipientMatches = sdkRequest.destination().toAddresses().size() == 1
				&& sdkRequest.destination().toAddresses().get(0).equals(properties.syntheticRecipient());
		RuntimeClassification classification = classify(senderAudit, recipientAudit, shape, sourceMatches,
				recipientMatches);
		return new SesRuntimeContextAudit(classification,
				HistoricalClassification.HISTORICAL_CONTEXT_NOT_RECONSTRUCTABLE, configurationSource,
				senderAudit, recipientAudit, shape, sourceMatches, recipientMatches, false, false,
				RetryBehavior.AWS_SDK_RETRIES_DISABLED_APPLICATION_BOUNDED);
	}

	private static RuntimeClassification classify(SesEndpointValueAudit sender,
			SesEndpointValueAudit recipient, SesRequestShapeAudit shape, boolean sourceMatches,
			boolean recipientMatches) {
		if (sender.exactApprovedMatch() == SesEndpointValueAudit.Comparison.COMPARISON_INPUT_UNAVAILABLE
				|| recipient.exactApprovedMatch() == SesEndpointValueAudit.Comparison.COMPARISON_INPUT_UNAVAILABLE) {
			return RuntimeClassification.COMPARISON_INPUT_UNAVAILABLE;
		}
		boolean exact = sender.exactApprovedMatch() == SesEndpointValueAudit.Comparison.MATCH
				&& recipient.exactApprovedMatch() == SesEndpointValueAudit.Comparison.MATCH;
		boolean boundedShape = shape.sourcePopulatedExactlyOnce() && shape.toCount() == 1
				&& shape.ccCount() == 0 && shape.bccCount() == 0 && !shape.duplicateRecipients()
				&& !shape.unexpectedOptionalFieldsPresent();
		return exact && boundedShape && sourceMatches && recipientMatches
				? RuntimeClassification.RUNTIME_CONTEXT_MATCH_CONFIRMED
				: RuntimeClassification.RUNTIME_CONTEXT_MISMATCH_FOUND;
	}
}
