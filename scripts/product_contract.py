from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/product/r4-420-product-semantics-v1.json"
ROLES = {"customer", "courier", "merchant", "analyst", "operator"}
NAMESPACES = {"accessibility", "locale", "notifications", "quiet_hours"}
CONSENT_STATES = {"NOT_ASKED", "GRANTED", "DENIED", "WITHDRAWN"}
PURPOSES = {
    "transactional_order",
    "dispatch_assignment",
    "operations_incident",
    "security",
    "marketing",
}
ACCESSIBILITY = {
    "keyboard_complete",
    "visible_focus",
    "screen_reader_names_and_status",
    "status_not_color_only",
    "reduced_motion_respected",
    "contrast_aa",
    "responsive_reflow",
    "errors_linked_to_controls",
    "live_updates_announced_without_focus_theft",
}
STATES = {
    "INTENT_RECORDED",
    "SUPPRESSED_NO_CONSENT",
    "DEFERRED_QUIET_HOURS",
    "READY",
    "PROVIDER_ACCEPTED",
    "FAILED_RETRYABLE",
    "FAILED_TERMINAL",
    "BOUNCED",
    "CANCELLED",
    "DELIVERED",
}
STATE_FLAGS = {
    "INTENT_RECORDED": (False, False),
    "SUPPRESSED_NO_CONSENT": (True, False),
    "DEFERRED_QUIET_HOURS": (False, False),
    "READY": (False, False),
    "PROVIDER_ACCEPTED": (False, False),
    "FAILED_RETRYABLE": (False, False),
    "FAILED_TERMINAL": (True, False),
    "BOUNCED": (True, False),
    "CANCELLED": (True, False),
    "DELIVERED": (True, True),
}
TRANSITIONS = {
    ("INTENT_RECORDED", "SUPPRESSED_NO_CONSENT", "consent_not_satisfied"),
    ("INTENT_RECORDED", "DEFERRED_QUIET_HOURS", "quiet_hours_apply"),
    ("INTENT_RECORDED", "READY", "consent_satisfied_and_not_quiet"),
    ("INTENT_RECORDED", "CANCELLED", "intent_cancelled"),
    ("DEFERRED_QUIET_HOURS", "READY", "eligible_and_consent_rechecked"),
    ("DEFERRED_QUIET_HOURS", "SUPPRESSED_NO_CONSENT", "consent_withdrawn"),
    ("DEFERRED_QUIET_HOURS", "CANCELLED", "intent_cancelled"),
    ("READY", "PROVIDER_ACCEPTED", "provider_acceptance_ack"),
    ("READY", "FAILED_RETRYABLE", "bounded_retryable_failure"),
    ("READY", "FAILED_TERMINAL", "terminal_provider_failure"),
    ("READY", "CANCELLED", "cancelled_before_attempt"),
    ("FAILED_RETRYABLE", "READY", "bounded_retry_due_and_consent_rechecked"),
    ("FAILED_RETRYABLE", "FAILED_TERMINAL", "retry_budget_exhausted"),
    ("FAILED_RETRYABLE", "CANCELLED", "intent_cancelled"),
    ("PROVIDER_ACCEPTED", "DELIVERED", "authenticated_provider_delivery_receipt"),
    ("PROVIDER_ACCEPTED", "FAILED_RETRYABLE", "provider_retryable_status"),
    ("PROVIDER_ACCEPTED", "FAILED_TERMINAL", "provider_terminal_status"),
    ("PROVIDER_ACCEPTED", "BOUNCED", "authenticated_provider_bounce_receipt"),
}


def load_contract(path: Path = CONTRACT) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("product contract must be a JSON object")
    return payload


def digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_contract(payload: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    if payload.get("schemaVersion") != 1 or payload.get("contractId") != "r4-420-product-semantics-v1":
        findings.append("identity:contract_version")
    if payload.get("status") != "FROZEN_LOCAL_CONTRACT":
        findings.append("status:not_frozen")

    authority = payload.get("authority", {})
    expected_authority = {
        "durableOwner": "java_business_api",
        "durableStore": "postgresql",
        "notificationIntent": "same_transaction_outbox",
        "pythonAuthority": "none",
        "llmAuthority": "none",
    }
    findings.extend(
        f"authority:{key}"
        for key, value in expected_authority.items()
        if authority.get(key) != value
    )
    if set(authority.get("identitySource", [])) != {
        "verified_tenant_id",
        "verified_principal_id",
        "verified_roles",
    }:
        findings.append("authority:verified_identity")
    if authority.get("preferenceKey") != ["tenant_id", "principal_id", "namespace"]:
        findings.append("authority:preference_key")
    concurrency = authority.get("writeConcurrency", {})
    if concurrency.get("versionField") != "version" or concurrency.get("precondition") != "expected_version_required":
        findings.append("authority:optimistic_concurrency")
    if concurrency.get("idempotencyScope") != [
        "tenant_id",
        "principal_id",
        "operation",
        "idempotency_key",
    ]:
        findings.append("authority:idempotency_scope")

    ownership = payload.get("ownership", {})
    role_records = ownership.get("roles", [])
    role_names = [record.get("role") for record in role_records if isinstance(record, dict)]
    if len(role_names) != len(ROLES) or set(role_names) != ROLES:
        findings.append("ownership:roles")
    for record in role_records:
        if not isinstance(record, dict) or set(record.get("namespaces", [])) != NAMESPACES:
            findings.append("ownership:namespaces")
            break
    required_ownership = {
        "selfRead": True,
        "selfWrite": True,
        "tenantMatchRequired": True,
        "principalMatchRequired": True,
        "crossTenant": "deny",
        "crossPrincipal": "deny",
        "roleImpersonation": "deny",
    }
    findings.extend(
        f"ownership:{key}" for key, value in required_ownership.items() if ownership.get(key) != value
    )
    if set(ownership.get("deliveryWorkerMayNotWrite", [])) != {"preferences", "consent"}:
        findings.append("ownership:worker_boundary")

    defaults = payload.get("defaults", {})
    channels = defaults.get("channels", {})
    if channels != {"in_app": True, "email": False, "sms": False, "push": False}:
        findings.append("defaults:channels_fail_closed")
    if defaults.get("locale") != "en-US" or defaults.get("timeZone") != "UTC":
        findings.append("defaults:locale_time_zone")
    accessibility_defaults = defaults.get("accessibility", {})
    if accessibility_defaults != {
        "theme": "system",
        "contrast": "system",
        "reducedMotion": "system",
        "textScale": 1.0,
        "screenReaderAnnouncements": "polite",
        "visibleFocus": True,
        "colorOnlyStatus": False,
    }:
        findings.append("defaults:accessibility")

    consent = payload.get("consent", {})
    if len(consent.get("states", [])) != len(CONSENT_STATES) or set(consent.get("states", [])) != CONSENT_STATES:
        findings.append("consent:states")
    if consent.get("key") != ["tenant_id", "principal_id", "purpose", "channel"]:
        findings.append("consent:key")
    if set(consent.get("recordFields", [])) != {"state", "version", "source", "captured_at", "policy_version"}:
        findings.append("consent:record_fields")
    if consent.get("dispatchRecheckRequired") is not True:
        findings.append("consent:dispatch_recheck")
    purpose_records = consent.get("purposes", [])
    purpose_names = [record.get("purpose") for record in purpose_records if isinstance(record, dict)]
    if len(purpose_names) != len(PURPOSES) or set(purpose_names) != PURPOSES:
        findings.append("consent:purposes")
    for record in purpose_records:
        if not isinstance(record, dict) or not set(record.get("roles", [])).issubset(ROLES):
            findings.append("consent:role_scope")
            break
        if record.get("externalBasis") != "explicit_grant":
            findings.append(f"consent:external_basis:{record.get('purpose', '<missing>')}")

    quiet = payload.get("quietHours", {})
    if quiet.get("zoneFormat") != "IANA_TZDB" or quiet.get("consentRecheckAfterDeferral") is not True:
        findings.append("quiet_hours:time_or_consent")
    if quiet.get("dstGap") != "advance_to_first_valid_instant" or quiet.get("dstOverlap") != "earlier_offset":
        findings.append("quiet_hours:dst")
    bypass = {
        item.get("purpose"): item.get("condition")
        for item in quiet.get("bypass", [])
        if isinstance(item, dict)
    }
    if len(quiet.get("bypass", [])) != 3 or bypass != {
        "security": "severity_critical",
        "operations_incident": "severity_critical_and_principal_on_call",
        "active_delivery_failure": "active_order_requires_immediate_action",
    }:
        findings.append("quiet_hours:bypass_scope")
    if quiet.get("marketingBypass") is not False or quiet.get("bypassAuditRequired") is not True:
        findings.append("quiet_hours:marketing_or_audit")

    requirements = payload.get("accessibilityRequirements", [])
    if len(requirements) != len(ACCESSIBILITY) or set(requirements) != ACCESSIBILITY:
        findings.append("accessibility:requirements")
    locale = payload.get("locale", {})
    if locale.get("format") != "BCP47" or locale.get("templateLocaleRecorded") is not True:
        findings.append("locale:identity")
    if locale.get("fallbackOrder") != ["exact_tag", "base_language", "en-US"]:
        findings.append("locale:fallback_order")
    if locale.get("missingExternalTemplate") != "fail_terminal_no_send":
        findings.append("locale:external_fallback")

    lifecycle = payload.get("notificationLifecycle", {})
    state_records = lifecycle.get("states", [])
    state_names = [state.get("name") for state in state_records if isinstance(state, dict)]
    if len(state_names) != len(STATES) or set(state_names) != STATES:
        findings.append("notification:states")
    actual_flags = {
        state.get("name"): (state.get("terminal"), state.get("delivered"))
        for state in state_records
        if isinstance(state, dict)
    }
    if actual_flags != STATE_FLAGS:
        findings.append("notification:state_flags")
    delivered_states = {
        state.get("name")
        for state in state_records
        if isinstance(state, dict) and state.get("delivered") is True
    }
    if delivered_states != {"DELIVERED"}:
        findings.append("notification:delivered_state")
    terminal_states = {
        state.get("name")
        for state in state_records
        if isinstance(state, dict) and state.get("terminal") is True
    }
    transitions = lifecycle.get("transitions", [])
    actual_transitions = {
        (transition.get("from"), transition.get("to"), transition.get("guard"))
        for transition in transitions
        if isinstance(transition, dict)
    }
    if len(transitions) != len(TRANSITIONS) or actual_transitions != TRANSITIONS:
        findings.append("notification:transition_graph")
    outgoing = {transition.get("from") for transition in transitions if isinstance(transition, dict)}
    if terminal_states & outgoing:
        findings.append("notification:terminal_transition")
    delivered_transitions = [
        transition for transition in transitions if isinstance(transition, dict) and transition.get("to") == "DELIVERED"
    ]
    if delivered_transitions != [
        {
            "from": "PROVIDER_ACCEPTED",
            "to": "DELIVERED",
            "guard": "authenticated_provider_delivery_receipt",
        }
    ]:
        findings.append("notification:delivery_transition")
    if any(
        transition.get("from") not in STATES or transition.get("to") not in STATES
        for transition in transitions
        if isinstance(transition, dict)
    ):
        findings.append("notification:unknown_transition_state")
    delivery = lifecycle.get("deliveryEvidence", {})
    if delivery.get("requiredForState") != "DELIVERED" or delivery.get("type") != "provider_delivery_ack":
        findings.append("notification:delivery_evidence")
    if delivery.get("providerAcceptanceIsDelivery") is not False or delivery.get("intentIsDelivery") is not False:
        findings.append("notification:false_delivery_claim")
    required_receipt = {"provider", "channel", "provider_message_id", "receipt_at", "authenticated_callback"}
    if set(delivery.get("fields", [])) != required_receipt or lifecycle.get("callbackAuthenticationRequired") is not True:
        findings.append("notification:authenticated_receipt")
    if not isinstance(lifecycle.get("maxAttempts"), int) or not 1 <= lifecycle["maxAttempts"] <= 10:
        findings.append("notification:bounded_retries")

    privacy = payload.get("privacy", {})
    if not {"principal_id", "address", "phone", "email", "message_body", "provider_message_id"}.issubset(
        set(privacy.get("forbiddenTelemetry", []))
    ):
        findings.append("privacy:telemetry")
    execution = payload.get("executionBoundary", {})
    if execution.get("realProviderSendAuthorized") is not False or execution.get("currentEvidence") != "contract_and_local_validator_only":
        findings.append("execution:external_send_boundary")
    if set(execution.get("nextImplementationTasks", [])) != {"R4-421", "R4-422", "R4-423", "R4-424"}:
        findings.append("execution:task_lineage")
    return sorted(set(findings))


def summary(payload: dict[str, Any]) -> dict[str, Any]:
    lifecycle = payload["notificationLifecycle"]
    return {
        "valid": True,
        "contractId": payload["contractId"],
        "digest": digest(payload),
        "roleCount": len(payload["ownership"]["roles"]),
        "purposeCount": len(payload["consent"]["purposes"]),
        "accessibilityRequirementCount": len(payload["accessibilityRequirements"]),
        "notificationStateCount": len(lifecycle["states"]),
        "notificationTransitionCount": len(lifecycle["transitions"]),
        "realProviderSendAuthorized": payload["executionBoundary"]["realProviderSendAuthorized"],
    }


def main() -> int:
    payload = load_contract()
    findings = validate_contract(payload)
    if findings:
        for finding in findings:
            print(f"ERROR: {finding}")
        return 1
    print(json.dumps(summary(payload), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
