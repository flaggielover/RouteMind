from __future__ import annotations

import unittest

from ses_iam_policy_differential_model import (
    evaluate_bounded_allow,
    for_all_values_string_equals,
    for_any_value_string_equals,
    normalize_context,
    string_equals,
)


class SesIamPolicyDifferentialModelTests(unittest.TestCase):
    RESOURCE = "arn:aws:ses:ap-northeast-1:REDACTED:identity/VERIFIED_SENDER"
    FROM = "sender@example.invalid"
    RECIPIENT = "recipient@example.invalid"

    def test_exact_identity_and_context_matches(self) -> None:
        self.assertTrue(
            evaluate_bounded_allow(
                action="ses:SendEmail",
                resource=self.RESOURCE,
                expected_resource=self.RESOURCE,
                from_address=self.FROM,
                expected_from=self.FROM,
                recipients=(self.RECIPIENT,),
                expected_recipients=(self.RECIPIENT,),
                secure_transport=True,
            )
        )

    def test_missing_from_or_extra_recipient_denies_statement(self) -> None:
        self.assertFalse(string_equals(None, self.FROM))
        self.assertFalse(
            evaluate_bounded_allow(
                action="ses:SendEmail",
                resource=self.RESOURCE,
                expected_resource=self.RESOURCE,
                from_address=None,
                expected_from=self.FROM,
                recipients=(self.RECIPIENT,),
                expected_recipients=(self.RECIPIENT,),
                secure_transport=True,
            )
        )
        self.assertFalse(
            for_all_values_string_equals(
                (self.RECIPIENT, "second@example.invalid"), (self.RECIPIENT,)
            )
        )

    def test_case_and_whitespace_are_not_string_equals_matches(self) -> None:
        self.assertFalse(string_equals(self.FROM.upper(), self.FROM))
        self.assertFalse(string_equals(f" {self.FROM}", self.FROM))

    def test_for_all_and_for_any_have_distinct_multivalue_semantics(self) -> None:
        values = (self.RECIPIENT, "additional@example.invalid")
        self.assertFalse(for_all_values_string_equals(values, (self.RECIPIENT,)))
        self.assertTrue(for_any_value_string_equals(values, (self.RECIPIENT,)))

    def test_missing_or_empty_recipients_are_vacuously_true_for_for_all(self) -> None:
        self.assertTrue(for_all_values_string_equals(None, (self.RECIPIENT,)))
        self.assertTrue(for_all_values_string_equals((), (self.RECIPIENT,)))

    def test_wildcard_resource_is_not_equivalent_to_exact_resource(self) -> None:
        self.assertNotEqual(self.RESOURCE, "*")
        self.assertFalse(
            evaluate_bounded_allow(
                action="ses:SendEmail",
                resource="*",
                expected_resource=self.RESOURCE,
                from_address=self.FROM,
                expected_from=self.FROM,
                recipients=(self.RECIPIENT,),
                expected_recipients=(self.RECIPIENT,),
                secure_transport=True,
            )
        )

    def test_context_shape_keeps_scalar_and_multivalue_explicit(self) -> None:
        self.assertEqual(
            normalize_context(from_address=self.FROM, recipients=[self.RECIPIENT]),
            (self.FROM, (self.RECIPIENT,)),
        )


if __name__ == "__main__":
    unittest.main()
