"""Offline IAM/SES condition-context model for differential audit aids only.

This module deliberately models IAM condition operators without contacting AWS.
It is not a provider emulator and its results must not be treated as live SES
behavior.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence


def _values(value: str | Iterable[str] | None) -> tuple[str, ...] | None:
    if value is None:
        return None
    if isinstance(value, str):
        return (value,)
    return tuple(value)


def string_equals(actual: str | None, expected: str) -> bool:
    """IAM StringEquals is exact and case-sensitive; absent keys do not match."""

    return actual is not None and actual == expected


def for_all_values_string_equals(
    actual: Sequence[str] | None, expected: Sequence[str]
) -> bool:
    """Model IAM's documented ForAllValues:StringEquals semantics.

    A missing or empty context set is vacuously true in IAM. A production
    policy that must require presence should pair it with a Null:false check.
    """

    if actual is None or not actual:
        return True
    return all(value in expected for value in actual)


def for_any_value_string_equals(
    actual: Sequence[str] | None, expected: Sequence[str]
) -> bool:
    """Model the contrasting ForAnyValue behavior for regression purposes."""

    if actual is None or not actual:
        return False
    return any(value in expected for value in actual)


def evaluate_bounded_allow(
    *,
    action: str,
    resource: str,
    expected_resource: str,
    from_address: str | None,
    expected_from: str,
    recipients: Sequence[str] | None,
    expected_recipients: Sequence[str],
    secure_transport: bool | None,
) -> bool:
    """Evaluate the current RouteMind policy shape using supplied context only."""

    return (
        action in {"ses:SendEmail", "ses:SendRawEmail"}
        and resource == expected_resource
        and string_equals(from_address, expected_from)
        and for_all_values_string_equals(recipients, expected_recipients)
        and secure_transport is True
    )


def normalize_context(
    *, from_address: str | None, recipients: Iterable[str] | None
) -> tuple[str | None, tuple[str, ...] | None]:
    """Keep test fixtures explicit about scalar versus multivalued context."""

    return from_address, _values(recipients)
