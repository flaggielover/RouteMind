"""Fail-closed R3-347 counterfactual Decision X-Ray support audit."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Literal

from routemind_compute.application.execution import canonical_digest

_SCHEMA = "routemind-counterfactual-xray-v1"
_CLAIM_BOUNDARY = "MODEL_SYSTEM_COUNTERFACTUAL_REPLAY_NOT_CAUSAL_INFERENCE"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DIMENSIONS = (
    "demand_signal",
    "supply_signal",
    "merchant_delay",
    "travel_time",
    "location_staleness",
    "compute_budget",
)
_OUTPUTS = (
    "original_decision",
    "perturbation",
    "counterfactual_decision",
    "objective_delta",
    "risk_delta",
    "minimality_verification",
    "lineage",
)
_IDENTITIES = (
    "source_decision_digest",
    "source_state_digest",
    "strategy_id",
    "strategy_version",
    "reference_data_digest",
    "replay_digest",
)
_SUPPORT = (
    "original_decision_summary",
    "captured_feature_state",
    "executable_policy_bundle",
    "perturbation_values",
    "counterfactual_decision_output",
    "objective_before_after",
    "risk_before_after",
    "replay_identity",
    "minimality_evidence",
)
_SOURCE_DIGESTS = {
    "decision_corpus_manifest": "d92c58cbf196e3f9ab7a157e575831f4c35a9508d3482a6f6ba90728c89e569b",
    "decision_corpus_records": "a9fbc9d01cf8bddff917e3b067342b091877bc24cbabbf9e776cc8e74e06799f",
    "policy_boundary_plan": "02304c1910463a30a481070382d76bb55c01c76be1bd6b7bcbeba972b14da5dd",
    "what_if_validity_plan": "81c52721886c646d2ff468f500c334566e3ed7f4f66bf0f63a9c4478f4b42023",
}


class CounterfactualXrayError(ValueError):
    """Raised when the replay plan or support input violates the contract."""


@dataclass(frozen=True, slots=True)
class CounterfactualXrayPlan:
    payload: Mapping[str, object]
    plan_digest: str
    manifest_sha256: str

    @property
    def study_id(self) -> str:
        return _text(self.payload, "study_id")


@dataclass(frozen=True, slots=True)
class CounterfactualXrayAudit:
    status: Literal["INSUFFICIENT_DATA", "READY_FOR_COUNTERFACTUAL_REPLAY"]
    plan_digest: str
    source_record_count: int
    replay_count: int
    available_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]
    perturbation_status: tuple[tuple[str, str], ...]
    output_status: tuple[tuple[str, str], ...]
    delta_status: str
    minimality_status: str
    lineage_status: str
    reason: str
    claim_boundary: str = _CLAIM_BOUNDARY


def load_counterfactual_xray_plan(path: Path | str) -> CounterfactualXrayPlan:
    plan_path = Path(path).expanduser().resolve()
    try:
        raw = plan_path.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CounterfactualXrayError("counterfactual X-Ray plan is not valid UTF-8 JSON") from exc
    if not isinstance(parsed, Mapping):
        raise CounterfactualXrayError("counterfactual X-Ray plan must be a JSON object")
    payload = dict(parsed)
    digest = _text(payload, "plan_digest")
    unsigned = dict(payload)
    del unsigned["plan_digest"]
    if canonical_digest(unsigned) != digest:
        raise CounterfactualXrayError("counterfactual X-Ray plan digest does not match content")
    _validate(payload)
    return CounterfactualXrayPlan(payload, digest, sha256(raw).hexdigest())


def audit_counterfactual_xray_support(
    plan: CounterfactualXrayPlan,
    artifact_support: Mapping[str, bool],
    source_record_count: int,
    replay_count: int,
) -> CounterfactualXrayAudit:
    if set(artifact_support) != set(_SUPPORT):
        raise CounterfactualXrayError("counterfactual X-Ray support fields mismatch")
    if any(
        isinstance(count, bool) or not isinstance(count, int) or count < 0
        for count in (source_record_count, replay_count)
    ):
        raise CounterfactualXrayError("counterfactual X-Ray counts must be non-negative integers")
    if replay_count > source_record_count:
        raise CounterfactualXrayError("replay count cannot exceed source record count")

    available = tuple(field for field in _SUPPORT if artifact_support[field])
    missing = tuple(field for field in _SUPPORT if not artifact_support[field])
    ready = not missing and replay_count > 0
    if ready:
        return CounterfactualXrayAudit(
            "READY_FOR_COUNTERFACTUAL_REPLAY",
            plan.plan_digest,
            source_record_count,
            replay_count,
            available,
            (),
            tuple((item, "READY_FOR_BOUNDED_PERTURBATION") for item in _DIMENSIONS),
            tuple((item, "READY_FOR_REPLAY_REPORT") for item in _OUTPUTS),
            "READY_FOR_SAME_METRIC_DELTAS",
            "READY_FOR_BOUNDED_MINIMALITY_CHECK",
            "READY_WITH_REQUIRED_IDENTITIES",
            "complete captured state, executable policy, replay output, deltas, and lineage exist",
        )

    reason = (
        "captured records are summaries without executable feature state, policy bundle, "
        "counterfactual output, deltas, replay identity, or minimality evidence"
        if missing
        else "no completed counterfactual replay is available"
    )
    return CounterfactualXrayAudit(
        "INSUFFICIENT_DATA",
        plan.plan_digest,
        source_record_count,
        replay_count,
        available,
        missing,
        tuple((item, "NOT_PERTURBED_NO_EXECUTABLE_REPLAY") for item in _DIMENSIONS),
        tuple((item, "NOT_REPORTED_INSUFFICIENT_REPLAY_SUPPORT") for item in _OUTPUTS),
        "NOT_COMPUTED_NO_COUNTERFACTUAL_OUTPUT",
        "NOT_VERIFIED_NO_EXECUTABLE_REPLAY",
        "SOURCE_SUMMARY_ONLY_NO_REPLAY_LINEAGE",
        reason,
    )


def _validate(value: Mapping[str, object]) -> None:
    required = {
        "schema_version",
        "task_id",
        "study_id",
        "frozen_at_utc",
        "question",
        "perturbation_dimensions",
        "required_outputs",
        "provenance_policy",
        "delta_policy",
        "minimality_policy",
        "support_requirements",
        "source_lineage",
        "execution_policy",
        "claim_boundary",
        "plan_digest",
    }
    if set(value) != required:
        raise CounterfactualXrayError("counterfactual X-Ray plan fields mismatch")
    if _text(value, "schema_version") != _SCHEMA or _text(value, "task_id") != "R3-347":
        raise CounterfactualXrayError("counterfactual X-Ray identity is unsupported")
    if _text(value, "study_id") != "r3-347-counterfactual-decision-xray-v1":
        raise CounterfactualXrayError("counterfactual X-Ray study identifier is not frozen")
    _text(value, "frozen_at_utc")
    _text(value, "question")
    if _text(value, "claim_boundary") != _CLAIM_BOUNDARY:
        raise CounterfactualXrayError("counterfactual X-Ray causal boundary is missing")
    if _texts(value, "perturbation_dimensions", "perturbation dimension") != _DIMENSIONS:
        raise CounterfactualXrayError("counterfactual X-Ray perturbations are not frozen")
    if _texts(value, "required_outputs", "required output") != _OUTPUTS:
        raise CounterfactualXrayError("counterfactual X-Ray outputs are not frozen")
    _validate_provenance(_mapping(value, "provenance_policy"))
    _validate_delta(_mapping(value, "delta_policy"))
    _validate_minimality(_mapping(value, "minimality_policy"))
    _validate_support(_mapping(value, "support_requirements"))
    _validate_lineage(_mapping(value, "source_lineage"))
    _validate_execution(_mapping(value, "execution_policy"))


def _validate_provenance(value: Mapping[str, object]) -> None:
    if set(value) != {"required_identities", "same_model_and_reference_data"}:
        raise CounterfactualXrayError("counterfactual provenance fields mismatch")
    if _texts(value, "required_identities", "provenance identity") != _IDENTITIES or not _bool(
        value, "same_model_and_reference_data"
    ):
        raise CounterfactualXrayError("counterfactual provenance policy is not frozen")


def _validate_delta(value: Mapping[str, object]) -> None:
    if set(value) != {"objective", "risk", "invented_composite_score"}:
        raise CounterfactualXrayError("counterfactual delta fields mismatch")
    if (
        _text(value, "objective") != "COUNTERFACTUAL_MINUS_ORIGINAL_SAME_OBJECTIVE_AND_UNITS"
        or _text(value, "risk") != "COUNTERFACTUAL_MINUS_ORIGINAL_SAME_RISK_AND_UNITS"
        or _bool(value, "invented_composite_score")
    ):
        raise CounterfactualXrayError("counterfactual delta policy is not frozen")


def _validate_minimality(value: Mapping[str, object]) -> None:
    required = {"required_when_computed", "search_order", "bounded_domain_only", "unverified_label"}
    if set(value) != required:
        raise CounterfactualXrayError("counterfactual minimality fields mismatch")
    if (
        not _bool(value, "required_when_computed")
        or _text(value, "search_order") != "L0_THEN_L1_LEXICOGRAPHIC"
        or not _bool(value, "bounded_domain_only")
        or _text(value, "unverified_label") != "NOT_VERIFIED_NO_EXECUTABLE_REPLAY"
    ):
        raise CounterfactualXrayError("counterfactual minimality policy is not frozen")


def _validate_support(value: Mapping[str, object]) -> None:
    if set(value) != {"required_fields", "source_status", "synthetic_substitution", "reason"}:
        raise CounterfactualXrayError("counterfactual support requirement fields mismatch")
    if _texts(value, "required_fields", "support field") != _SUPPORT:
        raise CounterfactualXrayError("counterfactual support fields are not frozen")
    if _text(value, "source_status") != "INSUFFICIENT_DATA" or _bool(
        value, "synthetic_substitution"
    ):
        raise CounterfactualXrayError("counterfactual support must remain fail-closed")
    _text(value, "reason")


def _validate_lineage(value: Mapping[str, object]) -> None:
    if set(value) != set(_SOURCE_DIGESTS):
        raise CounterfactualXrayError("counterfactual lineage fields mismatch")
    for key, expected in _SOURCE_DIGESTS.items():
        digest = _text(value, key)
        if digest != expected or not _SHA256.fullmatch(digest):
            raise CounterfactualXrayError(f"counterfactual {key} lineage is not frozen")


def _validate_execution(value: Mapping[str, object]) -> None:
    required = {
        "material_run_authorized",
        "r3_325_rerun",
        "write_external_artifacts",
        "synthetic_fill",
        "causal_inference_claim",
        "production_effect_claim",
        "manifest_changes",
        "resource_envelope",
    }
    if set(value) != required:
        raise CounterfactualXrayError("counterfactual execution fields mismatch")
    prohibited = any(
        _bool(value, key)
        for key in (
            "material_run_authorized",
            "r3_325_rerun",
            "write_external_artifacts",
            "synthetic_fill",
            "causal_inference_claim",
            "production_effect_claim",
        )
    )
    if prohibited:
        raise CounterfactualXrayError(
            "counterfactual execution must remain read-only and non-causal"
        )
    if _text(value, "manifest_changes") != "NEW_VERSION_REQUIRED":
        raise CounterfactualXrayError("counterfactual manifest change policy is not frozen")
    _text(value, "resource_envelope")


def _mapping(value: Mapping[str, object], key: str) -> Mapping[str, object]:
    selected = value.get(key)
    if not isinstance(selected, Mapping):
        raise CounterfactualXrayError(f"{key} must be an object")
    return selected


def _sequence(value: Mapping[str, object], key: str) -> Sequence[object]:
    selected = value.get(key)
    if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes, bytearray)):
        raise CounterfactualXrayError(f"{key} must be an array")
    return selected


def _texts(value: Mapping[str, object], key: str, label: str) -> tuple[str, ...]:
    return tuple(_text_item(item, label) for item in _sequence(value, key))


def _text(value: Mapping[str, object], key: str) -> str:
    selected = value.get(key)
    if not isinstance(selected, str) or not selected.strip() or len(selected) > 1024:
        raise CounterfactualXrayError(f"{key} must be non-empty text")
    return selected


def _text_item(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CounterfactualXrayError(f"{label} must be non-empty text")
    return value


def _bool(value: Mapping[str, object], key: str) -> bool:
    selected = value.get(key)
    if not isinstance(selected, bool):
        raise CounterfactualXrayError(f"{key} must be boolean")
    return selected


__all__ = [
    "CounterfactualXrayAudit",
    "CounterfactualXrayError",
    "CounterfactualXrayPlan",
    "audit_counterfactual_xray_support",
    "load_counterfactual_xray_plan",
]
