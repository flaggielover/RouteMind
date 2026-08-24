"""Aggregate Twin failure and non-fidelity evidence for R3-336."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Literal

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.twin_drift import TwinDriftOutcome
from routemind_compute.application.twin_held_out_validation import (
    TwinHeldOutValidationOutcome,
)
from routemind_compute.application.twin_split_contract import TwinSplitContract
from routemind_compute.application.twin_what_if_validity import (
    TwinWhatIfValidityOutcome,
)

_SCHEMA = "routemind-twin-non-fidelity-report-v1"
_CLAIM_BOUNDARY = "NON_FIDELITY_REPORT_DOES_NOT_ESTABLISH_TWIN_VALIDITY"
_SECTIONS = ("thresholds", "unsupported_regimes", "sensitivity", "data_limits", "claim_status")
_METRICS = (
    "assignment_rate",
    "scenario_risk_index",
    "dispatch_latency_seconds",
    "fallback_rate",
)
_STATUS = Literal["INSUFFICIENT_DATA"]


class TwinNonFidelityReportError(ValueError):
    """Raised when the R3-336 report plan or evidence lineage is unsafe."""


@dataclass(frozen=True, slots=True)
class TwinNonFidelityReportPlan:
    payload: Mapping[str, object]
    plan_digest: str
    manifest_sha256: str

    @property
    def report_id(self) -> str:
        return _text(self.payload, "report_id")


@dataclass(frozen=True, slots=True)
class NonFidelitySection:
    section_id: str
    status: str
    detail: str


@dataclass(frozen=True, slots=True)
class TwinNonFidelityReport:
    status: _STATUS
    plan_digest: str
    validation_plan_digest: str
    claim_status: str
    sections: tuple[NonFidelitySection, ...]
    claim_boundary: str = _CLAIM_BOUNDARY


def load_twin_non_fidelity_report_plan(path: Path | str) -> TwinNonFidelityReportPlan:
    """Load a content-addressed non-fidelity report plan without running experiments."""

    plan_path = Path(path).expanduser().resolve()
    try:
        raw = plan_path.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TwinNonFidelityReportError(
            "Twin non-fidelity report plan is not valid UTF-8 JSON"
        ) from exc
    if not isinstance(parsed, Mapping):
        raise TwinNonFidelityReportError("Twin non-fidelity report plan must be a JSON object")
    payload = dict(parsed)
    plan_digest = _text(payload, "plan_digest")
    unsigned = dict(payload)
    del unsigned["plan_digest"]
    if canonical_digest(unsigned) != plan_digest:
        raise TwinNonFidelityReportError(
            "Twin non-fidelity report plan digest does not match content"
        )
    _validate(payload)
    return TwinNonFidelityReportPlan(payload, plan_digest, sha256(raw).hexdigest())


def generate_twin_non_fidelity_report(
    plan: TwinNonFidelityReportPlan,
    split_contract: TwinSplitContract,
    validation_outcome: TwinHeldOutValidationOutcome,
    drift_outcome: TwinDriftOutcome,
    what_if_outcome: TwinWhatIfValidityOutcome,
) -> TwinNonFidelityReport:
    """Retain every no-data boundary and emit no unsupported scientific claim."""

    _validate_lineage(plan, split_contract, validation_outcome, drift_outcome, what_if_outcome)
    sections = (
        NonFidelitySection(
            "thresholds",
            "NOT_EVALUATED_NO_DATA",
            "All four R3-333 fidelity thresholds were frozen but not evaluated "
            "without observed held-out records.",
        ),
        NonFidelitySection(
            "unsupported_regimes",
            "NOT_ANALYZED_NO_DATA",
            "Time, zone, demand, and traffic regimes remain unsupported because "
            "both split artifacts contain zero records.",
        ),
        NonFidelitySection(
            "sensitivity",
            "NOT_RUN_NO_DATA",
            "Calibration, held-out, drift, and What-if sensitivity analyses were "
            "not run without authorized observations.",
        ),
        NonFidelitySection(
            "data_limits",
            "INSUFFICIENT_DATA",
            "No authorized immutable observed calibration or held-out dispatch "
            "outcome corpus is available locally; synthetic replay is prohibited.",
        ),
        NonFidelitySection(
            "claim_status",
            "C-NO-CLAIM",
            "No Twin-validity, external-validity, causal, stability, or "
            "simulation-transfer claim is permitted.",
        ),
    )
    return TwinNonFidelityReport(
        status="INSUFFICIENT_DATA",
        plan_digest=plan.plan_digest,
        validation_plan_digest=validation_outcome.plan_digest,
        claim_status="C-NO-CLAIM",
        sections=sections,
    )


def _validate_lineage(
    plan: TwinNonFidelityReportPlan,
    split_contract: TwinSplitContract,
    validation_outcome: TwinHeldOutValidationOutcome,
    drift_outcome: TwinDriftOutcome,
    what_if_outcome: TwinWhatIfValidityOutcome,
) -> None:
    source = _mapping(plan.payload, "source_digests")
    if _text(source, "split_contract") != split_contract.contract_digest:
        raise TwinNonFidelityReportError("split contract digest does not match report plan")
    if _text(source, "validation_plan") != validation_outcome.plan_digest:
        raise TwinNonFidelityReportError("validation plan digest does not match report plan")
    if _text(source, "drift_plan") != drift_outcome.plan_digest:
        raise TwinNonFidelityReportError("drift plan digest does not match report plan")
    if _text(source, "what_if_plan") != what_if_outcome.plan_digest:
        raise TwinNonFidelityReportError("What-if plan digest does not match report plan")
    if validation_outcome.outcome != "INSUFFICIENT_DATA":
        raise TwinNonFidelityReportError("non-fidelity report requires held-out INSUFFICIENT_DATA")
    if drift_outcome.status != "INSUFFICIENT_DATA":
        raise TwinNonFidelityReportError("non-fidelity report requires drift INSUFFICIENT_DATA")
    if what_if_outcome.status != "NO_VALIDITY_CLAIM":
        raise TwinNonFidelityReportError("non-fidelity report requires What-if NO_VALIDITY_CLAIM")
    if split_contract.data_status != "INSUFFICIENT_DATA":
        raise TwinNonFidelityReportError("non-fidelity report requires split INSUFFICIENT_DATA")


def _validate(value: Mapping[str, object]) -> None:
    required = {
        "schema_version",
        "task_id",
        "report_id",
        "frozen_at_utc",
        "question",
        "source_digests",
        "section_ids",
        "threshold_policy",
        "claim_policy",
        "claim_boundary",
        "plan_digest",
    }
    if set(value) != required:
        raise TwinNonFidelityReportError("Twin non-fidelity report plan fields mismatch")
    if _text(value, "schema_version") != _SCHEMA or _text(value, "task_id") != "R3-336":
        raise TwinNonFidelityReportError("Twin non-fidelity report plan identity is unsupported")
    if _text(value, "claim_boundary") != _CLAIM_BOUNDARY:
        raise TwinNonFidelityReportError("non-fidelity claim boundary is missing")
    _text(value, "question")
    source = _mapping(value, "source_digests")
    _exact(
        source,
        {
            "split_contract",
            "fidelity_protocol",
            "calibration_plan",
            "validation_plan",
            "drift_plan",
            "what_if_plan",
        },
        "source_digests",
    )
    for key in source:
        _digest(source, key)
    if (
        tuple(_text_mapping(item, "section id") for item in _sequence(value, "section_ids"))
        != _SECTIONS
    ):
        raise TwinNonFidelityReportError("non-fidelity section identity/order is not frozen")
    threshold = _mapping(value, "threshold_policy")
    _exact(threshold, {"metric_ids", "status_when_no_data"}, "threshold_policy")
    if (
        tuple(_text_mapping(item, "metric id") for item in _sequence(threshold, "metric_ids"))
        != _METRICS
    ):
        raise TwinNonFidelityReportError("non-fidelity metric identity/order is not frozen")
    if _text(threshold, "status_when_no_data") != "NOT_EVALUATED_NO_DATA":
        raise TwinNonFidelityReportError("missing threshold status is not frozen")
    claim = _mapping(value, "claim_policy")
    _exact(claim, {"status", "prohibited_claims"}, "claim_policy")
    if _text(claim, "status") != "C-NO-CLAIM":
        raise TwinNonFidelityReportError("non-fidelity claim status must be C-NO-CLAIM")
    if not _sequence(claim, "prohibited_claims"):
        raise TwinNonFidelityReportError("non-fidelity prohibited claims are required")


def _exact(value: Mapping[str, object], allowed: set[str], label: str) -> None:
    if set(value) != allowed:
        raise TwinNonFidelityReportError(f"{label} fields mismatch")


def _mapping(value: Mapping[str, object], key: str) -> Mapping[str, object]:
    return _mapping_value(value.get(key), key)


def _mapping_value(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TwinNonFidelityReportError(f"{label} must be an object")
    return value


def _sequence(value: Mapping[str, object], key: str) -> Sequence[object]:
    selected = value.get(key)
    if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes, bytearray)):
        raise TwinNonFidelityReportError(f"{key} must be an array")
    return selected


def _text(value: Mapping[str, object], key: str) -> str:
    selected = value.get(key)
    if not isinstance(selected, str) or not selected.strip() or len(selected) > 1024:
        raise TwinNonFidelityReportError(f"{key} must be non-empty text")
    return selected


def _text_mapping(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TwinNonFidelityReportError(f"{label} must be non-empty text")
    return value


def _digest(value: Mapping[str, object], key: str) -> str:
    selected = _text(value, key)
    if len(selected) != 64 or any(char not in "0123456789abcdef" for char in selected):
        raise TwinNonFidelityReportError(f"{key} must be a SHA-256 digest")
    return selected


__all__ = [
    "NonFidelitySection",
    "TwinNonFidelityReport",
    "TwinNonFidelityReportError",
    "TwinNonFidelityReportPlan",
    "generate_twin_non_fidelity_report",
    "load_twin_non_fidelity_report_plan",
]
