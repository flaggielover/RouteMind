package com.routemind.business.infrastructure.notification;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;

import com.routemind.business.application.notification.NotificationChannel;
import com.routemind.business.application.notification.NotificationRecipient;
import com.routemind.business.application.notification.NotificationRequest;
import com.routemind.business.application.notification.NotificationSender;
import com.routemind.business.domain.security.TenantId;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.Test;
import software.amazon.awssdk.services.ses.model.Body;
import software.amazon.awssdk.services.ses.model.Content;
import software.amazon.awssdk.services.ses.model.Destination;
import software.amazon.awssdk.services.ses.model.Message;
import software.amazon.awssdk.services.ses.model.SendEmailRequest;
import software.amazon.awssdk.services.ses.model.MessageTag;

class AwsSesRuntimeContextTests {

	private static final String SENDER = "synthetic-sender@example.invalid";
	private static final String RECIPIENT = "synthetic-recipient@example.invalid";

	@Test
	void exactSenderAndRecipientMatchUsesTheProductionRequestBuilder() {
		SesRuntimeContextAudit audit = audit(SENDER, RECIPIENT, SENDER, RECIPIENT);

		assertThat(audit.runtimeClassification())
				.isEqualTo(SesRuntimeContextAudit.RuntimeClassification.RUNTIME_CONTEXT_MATCH_CONFIRMED);
		assertThat(audit.sender().exactApprovedMatch()).isEqualTo(SesEndpointValueAudit.Comparison.MATCH);
		assertThat(audit.recipient().exactApprovedMatch()).isEqualTo(SesEndpointValueAudit.Comparison.MATCH);
		assertThat(audit.requestSourceMatchesNormalizedSender()).isTrue();
		assertThat(audit.requestRecipientMatchesNormalizedRecipient()).isTrue();
	}

	@Test
	void senderWhitespaceMismatchIsDetectedEvenWhenTheDomainValueTrims() {
		SesRuntimeContextAudit audit = audit(" " + SENDER + " ", RECIPIENT, SENDER, RECIPIENT);

		assertThat(audit.runtimeClassification())
				.isEqualTo(SesRuntimeContextAudit.RuntimeClassification.RUNTIME_CONTEXT_MISMATCH_FOUND);
		assertThat(audit.sender().exactApprovedMatch()).isEqualTo(SesEndpointValueAudit.Comparison.MISMATCH);
		assertThat(audit.sender().trimmedApprovedMatch()).isEqualTo(SesEndpointValueAudit.Comparison.MATCH);
		assertThat(audit.sender().leadingOrTrailingWhitespace()).isTrue();
		assertThat(audit.requestSourceMatchesNormalizedSender()).isTrue();
	}

	@Test
	void recipientWhitespaceMismatchIsDetectedWithoutChangingCardinality() {
		SesRuntimeContextAudit audit = audit(SENDER, " " + RECIPIENT + " ", SENDER, RECIPIENT);

		assertThat(audit.runtimeClassification())
				.isEqualTo(SesRuntimeContextAudit.RuntimeClassification.RUNTIME_CONTEXT_MISMATCH_FOUND);
		assertThat(audit.recipient().exactApprovedMatch()).isEqualTo(SesEndpointValueAudit.Comparison.MISMATCH);
		assertThat(audit.recipient().trimmedApprovedMatch()).isEqualTo(SesEndpointValueAudit.Comparison.MATCH);
		assertThat(audit.requestShape()).extracting(SesRequestShapeAudit::recipientCount,
				SesRequestShapeAudit::toCount, SesRequestShapeAudit::ccCount, SesRequestShapeAudit::bccCount)
				.containsExactly(1, 1, 0, 0);
	}

	@Test
	void detectsDisplayNameUnicodeNormalizationAndCaseDifferencesStructurally() {
		SesEndpointValueAudit display = SesEndpointValueAudit.inspect("RouteMind <" + SENDER + ">", null, null);
		SesEndpointValueAudit unicode = SesEndpointValueAudit.inspect("synthe\u0301tic@example.invalid", null, null);
		SesEndpointValueAudit upper = SesEndpointValueAudit.inspect("Synthetic@example.invalid", null, null);

		assertThat(display.displayNameSyntax()).isTrue();
		assertThat(display.angleBracketSyntax()).isTrue();
		assertThat(unicode.unicodeNormalizationDifference()).isTrue();
		assertThat(upper.caseNormalizationChangesValue()).isTrue();
	}

	@Test
	void productionFactoryRejectsDomainEndpointsOutsideTheBoundedConfiguration() {
		NotificationSesProperties properties = properties(SENDER, RECIPIENT);
		AwsSesRequestFactory factory = new AwsSesRequestFactory();

		assertThatIllegalArgumentException().isThrownBy(() -> factory.create(
				request("other-sender@example.invalid", RECIPIENT), properties));
		assertThatIllegalArgumentException().isThrownBy(() -> factory.create(
				request(SENDER, "other-recipient@example.invalid"), properties));
	}

	@Test
	void requestShapeReportsCardinalityAndUnexpectedOptionalFields() {
		SendEmailRequest bounded = new AwsSesRequestFactory().create(request(SENDER, RECIPIENT),
				properties(SENDER, RECIPIENT));
		SesRequestShapeAudit boundedShape = SesRequestShapeAudit.inspect(bounded);
		assertThat(boundedShape.sourcePopulatedExactlyOnce()).isTrue();
		assertThat(boundedShape.recipientCount()).isEqualTo(1);
		assertThat(boundedShape.ccCount()).isZero();
		assertThat(boundedShape.bccCount()).isZero();
		assertThat(boundedShape.duplicateRecipients()).isFalse();
		assertThat(boundedShape.unexpectedOptionalFieldsPresent()).isFalse();

		SendEmailRequest unexpected = SendEmailRequest.builder()
				.source(SENDER)
				.destination(Destination.builder().toAddresses(RECIPIENT, RECIPIENT)
						.ccAddresses("synthetic-cc@example.invalid").build())
				.replyToAddresses("synthetic-reply@example.invalid")
				.returnPath("synthetic-return@example.invalid")
				.sourceArn("synthetic-source-authorization-reference")
				.returnPathArn("synthetic-return-authorization-reference")
				.configurationSetName("synthetic-configuration")
				.tags(MessageTag.builder().name("synthetic").value("true").build())
				.message(message())
				.build();
		SesRequestShapeAudit unexpectedShape = SesRequestShapeAudit.inspect(unexpected);
		assertThat(unexpectedShape.recipientCount()).isEqualTo(3);
		assertThat(unexpectedShape.duplicateRecipients()).isTrue();
		assertThat(unexpectedShape.delegatedAuthorizationFieldsPresent()).isTrue();
		assertThat(unexpectedShape.unexpectedOptionalFieldsPresent()).isTrue();
	}

	@Test
	void comparisonInputAbsenceIsExplicitAndNeverSubstitutesAFixture() {
		SesRuntimeContextAudit audit = audit(SENDER, RECIPIENT, null, null);

		assertThat(audit.runtimeClassification())
				.isEqualTo(SesRuntimeContextAudit.RuntimeClassification.COMPARISON_INPUT_UNAVAILABLE);
		assertThat(audit.historicalClassification())
				.isEqualTo(SesRuntimeContextAudit.HistoricalClassification.HISTORICAL_CONTEXT_NOT_RECONSTRUCTABLE);
	}

	@Test
	void currentProcessContextIsAuditedWithoutRevealingValues() {
		String rawSender = System.getenv("ROUTEMIND_NOTIFICATION_SENDER");
		String rawRecipient = System.getenv("ROUTEMIND_NOTIFICATION_SYNTHETIC_RECIPIENT");
		Assumptions.assumeTrue(rawSender != null && !rawSender.isBlank()
				&& rawRecipient != null && !rawRecipient.isBlank(),
				"process-scoped notification endpoints are unavailable");

		SesRuntimeContextAudit audit = audit(rawSender, rawRecipient, null, null);
		System.out.println("RUNTIME_CONTEXT_CLASSIFICATION=" + audit.runtimeClassification());
		System.out.println("HISTORICAL_CONTEXT_CLASSIFICATION=" + audit.historicalClassification());
		System.out.println("SENDER_PRESENT=" + audit.sender().present());
		System.out.println("SENDER_RAW_EQUALS_NORMALIZED=" + audit.sender().rawEqualsNormalized());
		System.out.println("SENDER_TRIMMED_EQUALS_NORMALIZED=" + audit.sender().trimmedEqualsNormalized());
		System.out.println("SENDER_HAS_BOUNDARY_WHITESPACE=" + audit.sender().leadingOrTrailingWhitespace());
		System.out.println("SENDER_HAS_DISPLAY_NAME=" + audit.sender().displayNameSyntax());
		System.out.println("SENDER_HAS_UNICODE_NORMALIZATION_DIFFERENCE="
				+ audit.sender().unicodeNormalizationDifference());
		System.out.println("SENDER_CASE_NORMALIZATION_CHANGES_VALUE="
				+ audit.sender().caseNormalizationChangesValue());
		System.out.println("RECIPIENT_PRESENT=" + audit.recipient().present());
		System.out.println("RECIPIENT_RAW_EQUALS_NORMALIZED=" + audit.recipient().rawEqualsNormalized());
		System.out.println("RECIPIENT_TRIMMED_EQUALS_NORMALIZED=" + audit.recipient().trimmedEqualsNormalized());
		System.out.println("RECIPIENT_HAS_BOUNDARY_WHITESPACE="
				+ audit.recipient().leadingOrTrailingWhitespace());
		System.out.println("RECIPIENT_HAS_DISPLAY_NAME=" + audit.recipient().displayNameSyntax());
		System.out.println("RECIPIENT_HAS_UNICODE_NORMALIZATION_DIFFERENCE="
				+ audit.recipient().unicodeNormalizationDifference());
		System.out.println("RECIPIENT_CASE_NORMALIZATION_CHANGES_VALUE="
				+ audit.recipient().caseNormalizationChangesValue());
		System.out.println("REQUEST_SOURCE_MATCHES_NORMALIZED=" + audit.requestSourceMatchesNormalizedSender());
		System.out.println("REQUEST_RECIPIENT_MATCHES_NORMALIZED="
				+ audit.requestRecipientMatchesNormalizedRecipient());
		System.out.println("REQUEST_TO_COUNT=" + audit.requestShape().toCount());
		System.out.println("REQUEST_CC_COUNT=" + audit.requestShape().ccCount());
		System.out.println("REQUEST_BCC_COUNT=" + audit.requestShape().bccCount());
		System.out.println("REQUEST_UNEXPECTED_OPTIONAL_FIELDS="
				+ audit.requestShape().unexpectedOptionalFieldsPresent());
		System.out.println("ENDPOINT_OVERRIDE_PRESENT=" + audit.endpointOverridePresent());
		System.out.println("REGION_OVERRIDE_PRESENT=" + audit.regionOverridePresent());
		System.out.println("RETRY_BEHAVIOR=" + audit.retryBehavior());
	}

	private static SesRuntimeContextAudit audit(String rawSender, String rawRecipient,
			String approvedSender, String approvedRecipient) {
		NotificationSesProperties properties = properties(rawSender, rawRecipient);
		return SesRuntimeContextAudit.inspect(rawSender, rawRecipient, approvedSender, approvedRecipient,
				request(properties.sender(), properties.syntheticRecipient()), properties,
				SesRuntimeContextAudit.ConfigurationSource.PROCESS_ENVIRONMENT, new AwsSesRequestFactory());
	}

	private static NotificationSesProperties properties(String sender, String recipient) {
		return new NotificationSesProperties(true, "routemind-ses", "ap-northeast-1", sender, recipient);
	}

	private static NotificationRequest request(String sender, String recipient) {
		return new NotificationRequest(
				UUID.fromString("11111111-1111-4111-8111-111111111111"),
				new TenantId(UUID.fromString("22222222-2222-4222-8222-222222222222")),
				UUID.fromString("33333333-3333-4333-8333-333333333333"),
				"r4-422-offline-audit", NotificationChannel.EMAIL,
				new NotificationRecipient(recipient), new NotificationSender(sender),
				"r4-422-synthetic", "Synthetic subject", "Synthetic body", 1,
				UUID.fromString("44444444-4444-4444-8444-444444444444"),
				Instant.parse("2026-08-29T00:00:00Z"), Map.of("privacy_boundary", "synthetic-only"));
	}

	private static Message message() {
		Content content = Content.builder().data("synthetic").build();
		return Message.builder().subject(content).body(Body.builder().text(content).build()).build();
	}
}
