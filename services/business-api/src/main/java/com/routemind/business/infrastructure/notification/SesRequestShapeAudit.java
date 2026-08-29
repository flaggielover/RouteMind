package com.routemind.business.infrastructure.notification;

import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import software.amazon.awssdk.services.ses.model.Destination;
import software.amazon.awssdk.services.ses.model.SendEmailRequest;

/** Non-content shape of an SES request, suitable for logs and durable evidence. */
public record SesRequestShapeAudit(boolean sourcePresent, boolean sourcePopulatedExactlyOnce,
		int recipientCount, int toCount, int ccCount, int bccCount, boolean duplicateRecipients,
		int replyToCount, boolean returnPathPresent, boolean sourceArnPresent,
		boolean returnPathArnPresent, boolean configurationSetPresent, int tagCount,
		boolean delegatedAuthorizationFieldsPresent, boolean unexpectedOptionalFieldsPresent) {

	public static SesRequestShapeAudit inspect(SendEmailRequest request) {
		Objects.requireNonNull(request, "request");
		Destination destination = request.destination();
		List<String> to = destination == null ? List.of() : destination.toAddresses();
		List<String> cc = destination == null ? List.of() : destination.ccAddresses();
		List<String> bcc = destination == null ? List.of() : destination.bccAddresses();
		int recipientCount = to.size() + cc.size() + bcc.size();
		boolean duplicates = new HashSet<>(concat(to, cc, bcc)).size() != recipientCount;
		boolean sourceArn = hasText(request.sourceArn());
		boolean returnPathArn = hasText(request.returnPathArn());
		boolean delegated = sourceArn || returnPathArn;
		boolean unexpected = !request.replyToAddresses().isEmpty()
				|| hasText(request.returnPath())
				|| delegated
				|| hasText(request.configurationSetName())
				|| !request.tags().isEmpty();
		boolean sourcePresent = hasText(request.source());
		return new SesRequestShapeAudit(sourcePresent, sourcePresent, recipientCount, to.size(), cc.size(),
				bcc.size(), duplicates, request.replyToAddresses().size(), hasText(request.returnPath()),
				sourceArn, returnPathArn, hasText(request.configurationSetName()), request.tags().size(),
				delegated, unexpected);
	}

	private static List<String> concat(List<String> first, List<String> second, List<String> third) {
		var values = new java.util.ArrayList<String>(first.size() + second.size() + third.size());
		values.addAll(first);
		values.addAll(second);
		values.addAll(third);
		return values;
	}

	private static boolean hasText(String value) {
		return value != null && !value.isBlank();
	}
}
