from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path
from typing import Literal, cast

import pytest

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.twin_calibration import (
    execute_bounded_twin_calibration,
    load_twin_calibration_plan,
)
from routemind_compute.application.twin_drift import (
    TwinDriftOutcome,
    execute_twin_drift_report,
    load_twin_drift_plan,
)
from routemind_compute.application.twin_fidelity_protocol import load_twin_fidelity_protocol
from routemind_compute.application.twin_held_out_validation import (
    TwinHeldOutValidationOutcome,
    execute_twin_held_out_validation,
    load_twin_held_out_validation_plan,
)
from routemind_compute.application.twin_non_fidelity_report import (
    TwinNonFidelityReportError,
    TwinNonFidelityReportPlan,
    generate_twin_non_fidelity_report,
    load_twin_non_fidelity_report_plan,
)
from routemind_compute.application.twin_split_contract import (
    TwinSplitContract,
    load_twin_split_contract,
)
from routemind_compute.application.twin_what_if_validity import (
    TwinWhatIfValidityOutcome,
    assess_twin_what_if_validity,
    load_twin_what_if_validity_plan,
)

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "docs" / "research" / "r3" / "manifests" / "twin" / "r3-336-twin-non-fidelity-v1.json"
CALIBRATION = (
    ROOT / "docs" / "research" / "r3" / "manifests" / "twin" / "r3-331-calibration-plan-v1.json"
)
VALIDATION = (
    ROOT / "docs" / "research" / "r3" / "manifests" / "twin" / "r3-332-held-out-validation-v1.json"
)
DRIFT = (
    ROOT / "docs" / "research" / "r3" / "manifests" / "twin" / "r3-334-calibration-drift-v1.json"
)
WHAT_IF = (
    ROOT / "docs" / "research" / "r3" / "manifests" / "twin" / "r3-335-what-if-validity-v1.json"
)
SPLIT = (
    ROOT / "docs" / "research" / "r3" / "manifests" / "twin" / "r3-330-twin-split-contract-v1.json"
)
PROTOCOL = (
    ROOT / "docs" / "research" / "r3" / "manifests" / "twin" / "r3-333-fidelity-protocol-v1.json"
)


def _payload() -> dict[str, object]:
    parsed: object = json.loads(PLAN.read_text(encoding="utf-8"))
    if not isinstance(parsed, Mapping):
        raise AssertionError("fixture must be an object")
    return cast(dict[str, object], parsed)


def _mapping(value: object) -> dict[str, object]:
    return dict(cast(Mapping[str, object], value))


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    unsigned = dict(payload)
    unsigned["plan_digest"] = canonical_digest(
        {key: value for key, value in unsigned.items() if key != "plan_digest"}
    )
    path = tmp_path / "report.json"
    path.write_text(json.dumps(unsigned, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _loaded() -> tuple[
    TwinNonFidelityReportPlan,
    TwinSplitContract,
    TwinHeldOutValidationOutcome,
    TwinDriftOutcome,
    TwinWhatIfValidityOutcome,
]:
    report = load_twin_non_fidelity_report_plan(PLAN)
    calibration = load_twin_calibration_plan(CALIBRATION)
    validation_plan = load_twin_held_out_validation_plan(VALIDATION)
    drift_plan = load_twin_drift_plan(DRIFT)
    what_if_plan = load_twin_what_if_validity_plan(WHAT_IF)
    split = load_twin_split_contract(SPLIT)
    protocol = load_twin_fidelity_protocol(PROTOCOL)
    calibration_outcome = execute_bounded_twin_calibration(calibration, split, protocol)
    validation_outcome = execute_twin_held_out_validation(
        validation_plan, split, protocol, calibration, calibration_outcome
    )
    drift_outcome = execute_twin_drift_report(drift_plan, split, validation_outcome)
    what_if_outcome = assess_twin_what_if_validity(what_if_plan, validation_outcome)
    return report, split, validation_outcome, drift_outcome, what_if_outcome


def test_report_retains_all_no_data_sections_and_claim_boundary() -> None:
    report, split, validation, drift, what_if = _loaded()
    result = generate_twin_non_fidelity_report(report, split, validation, drift, what_if)
    assert report.report_id == "r3-336-twin-non-fidelity-v1"
    assert result.status == "INSUFFICIENT_DATA"
    assert result.claim_status == "C-NO-CLAIM"
    assert [section.section_id for section in result.sections] == [
        "thresholds",
        "unsupported_regimes",
        "sensitivity",
        "data_limits",
        "claim_status",
    ]
    assert [section.status for section in result.sections] == [
        "NOT_EVALUATED_NO_DATA",
        "NOT_ANALYZED_NO_DATA",
        "NOT_RUN_NO_DATA",
        "INSUFFICIENT_DATA",
        "C-NO-CLAIM",
    ]


def test_plan_rejects_digest_json_identity_and_shape(tmp_path: Path) -> None:
    payload = _payload()
    payload["question"] = "changed"
    forged = tmp_path / "forged.json"
    forged.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(TwinNonFidelityReportError, match="digest"):
        load_twin_non_fidelity_report_plan(forged)

    scalar = tmp_path / "scalar.json"
    scalar.write_text("[]", encoding="utf-8")
    with pytest.raises(TwinNonFidelityReportError, match="JSON object"):
        load_twin_non_fidelity_report_plan(scalar)

    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b"not-json")
    with pytest.raises(TwinNonFidelityReportError, match="UTF-8 JSON"):
        load_twin_non_fidelity_report_plan(invalid)

    payload = _payload()
    del payload["question"]
    with pytest.raises(TwinNonFidelityReportError, match="fields mismatch"):
        load_twin_non_fidelity_report_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["task_id"] = "R3-335"
    with pytest.raises(TwinNonFidelityReportError, match="identity"):
        load_twin_non_fidelity_report_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["claim_boundary"] = "other"
    with pytest.raises(TwinNonFidelityReportError, match="claim boundary"):
        load_twin_non_fidelity_report_plan(_write(tmp_path, payload))


def test_plan_rejects_section_threshold_and_claim_policy_drift(tmp_path: Path) -> None:
    payload = _payload()
    payload["section_ids"] = ["claim_status"]
    with pytest.raises(TwinNonFidelityReportError, match="section identity"):
        load_twin_non_fidelity_report_plan(_write(tmp_path, payload))

    payload = _payload()
    threshold = _mapping(payload["threshold_policy"])
    threshold["status_when_no_data"] = "PASS"
    payload["threshold_policy"] = threshold
    with pytest.raises(TwinNonFidelityReportError, match="threshold status"):
        load_twin_non_fidelity_report_plan(_write(tmp_path, payload))

    payload = _payload()
    threshold = _mapping(payload["threshold_policy"])
    threshold["metric_ids"] = ["assignment_rate"]
    payload["threshold_policy"] = threshold
    with pytest.raises(TwinNonFidelityReportError, match="metric identity"):
        load_twin_non_fidelity_report_plan(_write(tmp_path, payload))

    payload = _payload()
    claim = _mapping(payload["claim_policy"])
    claim["status"] = "C-PASS"
    payload["claim_policy"] = claim
    with pytest.raises(TwinNonFidelityReportError, match="C-NO-CLAIM"):
        load_twin_non_fidelity_report_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["threshold_policy"] = "invalid"
    with pytest.raises(TwinNonFidelityReportError, match="object"):
        load_twin_non_fidelity_report_plan(_write(tmp_path, payload))

    payload = _payload()
    threshold = _mapping(payload["threshold_policy"])
    threshold["unexpected"] = True
    payload["threshold_policy"] = threshold
    with pytest.raises(TwinNonFidelityReportError, match="threshold_policy fields mismatch"):
        load_twin_non_fidelity_report_plan(_write(tmp_path, payload))

    payload = _payload()
    threshold = _mapping(payload["threshold_policy"])
    threshold["metric_ids"] = "invalid"
    payload["threshold_policy"] = threshold
    with pytest.raises(TwinNonFidelityReportError, match="array"):
        load_twin_non_fidelity_report_plan(_write(tmp_path, payload))

    payload = _payload()
    claim = _mapping(payload["claim_policy"])
    claim["prohibited_claims"] = []
    payload["claim_policy"] = claim
    with pytest.raises(TwinNonFidelityReportError, match="prohibited claims"):
        load_twin_non_fidelity_report_plan(_write(tmp_path, payload))


def test_plan_rejects_nested_types_and_lineage(tmp_path: Path) -> None:
    report, split, validation, drift, what_if = _loaded()
    source = _mapping(report.payload["source_digests"])
    source["split_contract"] = "a" * 64
    altered = TwinNonFidelityReportPlan(
        {**report.payload, "source_digests": source}, report.plan_digest, report.manifest_sha256
    )
    with pytest.raises(TwinNonFidelityReportError, match="split contract digest"):
        generate_twin_non_fidelity_report(altered, split, validation, drift, what_if)

    source = _mapping(report.payload["source_digests"])
    source["drift_plan"] = "a" * 64
    altered = TwinNonFidelityReportPlan(
        {**report.payload, "source_digests": source}, report.plan_digest, report.manifest_sha256
    )
    with pytest.raises(TwinNonFidelityReportError, match="drift plan digest"):
        generate_twin_non_fidelity_report(altered, split, validation, drift, what_if)

    non_data_validation = type(validation)(
        "VALIDATED_FOR_SCOPE",
        validation.plan_digest,
        validation.split_contract_digest,
        validation.fidelity_protocol_digest,
        validation.calibration_status,
        validation.held_out_record_count,
        validation.metrics,
        validation.reason,
    )
    with pytest.raises(TwinNonFidelityReportError, match="held-out INSUFFICIENT"):
        generate_twin_non_fidelity_report(report, split, non_data_validation, drift, what_if)

    non_data_drift = TwinDriftOutcome(
        cast(Literal["INSUFFICIENT_DATA"], "READY"),
        drift.plan_digest,
        drift.split_contract_digest,
        drift.validation_plan_digest,
        "READY",
        drift.fidelity_degradation_status,
        drift.regimes,
        drift.reason,
    )
    with pytest.raises(TwinNonFidelityReportError, match="drift INSUFFICIENT"):
        generate_twin_non_fidelity_report(report, split, validation, non_data_drift, what_if)

    non_data_what_if = type(what_if)(
        "SCOPE_ONLY",
        what_if.plan_digest,
        what_if.validation_plan_digest,
        what_if.allowed_scope,
        what_if.modes,
        what_if.reason,
    )
    with pytest.raises(TwinNonFidelityReportError, match="What-if NO_VALIDITY"):
        generate_twin_non_fidelity_report(report, split, validation, drift, non_data_what_if)

    non_data_split = TwinSplitContract(
        {
            **split.payload,
            "data_availability": {
                **_mapping(split.payload["data_availability"]),
                "status": "AVAILABLE",
            },
        },
        split.contract_digest,
        split.manifest_sha256,
    )
    with pytest.raises(TwinNonFidelityReportError, match="split INSUFFICIENT"):
        generate_twin_non_fidelity_report(report, non_data_split, validation, drift, what_if)

    source = _mapping(report.payload["source_digests"])
    source["validation_plan"] = "a" * 64
    altered = TwinNonFidelityReportPlan(
        {**report.payload, "source_digests": source}, report.plan_digest, report.manifest_sha256
    )
    with pytest.raises(TwinNonFidelityReportError, match="validation plan digest"):
        generate_twin_non_fidelity_report(altered, split, validation, drift, what_if)

    source = _mapping(report.payload["source_digests"])
    source["what_if_plan"] = "a" * 64
    altered = TwinNonFidelityReportPlan(
        {**report.payload, "source_digests": source}, report.plan_digest, report.manifest_sha256
    )
    with pytest.raises(TwinNonFidelityReportError, match="What-if plan digest"):
        generate_twin_non_fidelity_report(altered, split, validation, drift, what_if)

    payload = _payload()
    payload["source_digests"] = "invalid"
    with pytest.raises(TwinNonFidelityReportError, match="object"):
        load_twin_non_fidelity_report_plan(_write(tmp_path, payload))

    payload = _payload()
    threshold = _mapping(payload["threshold_policy"])
    threshold["metric_ids"] = [None]
    payload["threshold_policy"] = threshold
    with pytest.raises(TwinNonFidelityReportError, match="metric id must be non-empty text"):
        load_twin_non_fidelity_report_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["question"] = ""
    with pytest.raises(TwinNonFidelityReportError, match="question must be non-empty text"):
        load_twin_non_fidelity_report_plan(_write(tmp_path, payload))

    payload = _payload()
    source = _mapping(payload["source_digests"])
    source["split_contract"] = "invalid"
    payload["source_digests"] = source
    with pytest.raises(TwinNonFidelityReportError, match="split_contract must be a SHA-256 digest"):
        load_twin_non_fidelity_report_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["section_ids"] = [
        None,
        "unsupported_regimes",
        "sensitivity",
        "data_limits",
        "claim_status",
    ]
    with pytest.raises(TwinNonFidelityReportError, match="section id must be non-empty text"):
        load_twin_non_fidelity_report_plan(_write(tmp_path, payload))


def test_plan_file_digest_is_stable() -> None:
    first = load_twin_non_fidelity_report_plan(PLAN)
    second = load_twin_non_fidelity_report_plan(PLAN)
    assert first.manifest_sha256 == second.manifest_sha256
    assert first.manifest_sha256 == sha256(PLAN.read_bytes()).hexdigest()
