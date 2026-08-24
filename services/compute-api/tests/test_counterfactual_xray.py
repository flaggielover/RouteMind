from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from routemind_compute.application.counterfactual_xray import (
    CounterfactualXrayError,
    audit_counterfactual_xray_support,
    load_counterfactual_xray_plan,
)
from routemind_compute.application.execution import canonical_digest

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "docs/research/r3/manifests/rads/r3-347-counterfactual-xray-v1.json"
SUPPORT = (
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


def _payload() -> dict[str, object]:
    parsed: object = json.loads(PLAN.read_text(encoding="utf-8"))
    return dict(cast(Mapping[str, object], parsed))


def _mapping(value: object) -> dict[str, object]:
    return dict(cast(Mapping[str, object], value))


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    value = dict(payload)
    value["plan_digest"] = canonical_digest({k: v for k, v in value.items() if k != "plan_digest"})
    path = tmp_path / "counterfactual-xray.json"
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return path


def test_plan_freezes_replay_delta_minimality_and_lineage() -> None:
    plan = load_counterfactual_xray_plan(PLAN)
    assert plan.study_id == "r3-347-counterfactual-decision-xray-v1"
    assert plan.manifest_sha256 == sha256(PLAN.read_bytes()).hexdigest()
    assert (
        plan.payload["claim_boundary"] == "MODEL_SYSTEM_COUNTERFACTUAL_REPLAY_NOT_CAUSAL_INFERENCE"
    )


def test_current_corpus_refuses_counterfactual_replay() -> None:
    support = {field: False for field in SUPPORT}
    support["original_decision_summary"] = True
    audit = audit_counterfactual_xray_support(
        load_counterfactual_xray_plan(PLAN), support, source_record_count=2, replay_count=0
    )
    assert audit.status == "INSUFFICIENT_DATA"
    assert audit.available_fields == ("original_decision_summary",)
    assert audit.source_record_count == 2
    assert audit.replay_count == 0
    assert all(
        status == "NOT_PERTURBED_NO_EXECUTABLE_REPLAY" for _, status in audit.perturbation_status
    )
    assert all(
        status == "NOT_REPORTED_INSUFFICIENT_REPLAY_SUPPORT" for _, status in audit.output_status
    )
    assert audit.minimality_status == "NOT_VERIFIED_NO_EXECUTABLE_REPLAY"
    assert audit.claim_boundary.endswith("NOT_CAUSAL_INFERENCE")


def test_complete_support_requires_a_completed_replay() -> None:
    plan = load_counterfactual_xray_plan(PLAN)
    support = {field: True for field in SUPPORT}
    empty = audit_counterfactual_xray_support(plan, support, 1, 0)
    assert empty.status == "INSUFFICIENT_DATA"
    assert empty.reason == "no completed counterfactual replay is available"
    ready = audit_counterfactual_xray_support(plan, support, 1, 1)
    assert ready.status == "READY_FOR_COUNTERFACTUAL_REPLAY"
    assert ready.missing_fields == ()
    assert ready.delta_status == "READY_FOR_SAME_METRIC_DELTAS"
    assert ready.minimality_status == "READY_FOR_BOUNDED_MINIMALITY_CHECK"
    assert ready.lineage_status == "READY_WITH_REQUIRED_IDENTITIES"


def test_audit_rejects_support_and_count_shape() -> None:
    plan = load_counterfactual_xray_plan(PLAN)
    with pytest.raises(CounterfactualXrayError, match="support fields"):
        audit_counterfactual_xray_support(plan, {"original_decision_summary": True}, 1, 0)
    with pytest.raises(CounterfactualXrayError, match="non-negative integers"):
        audit_counterfactual_xray_support(plan, {field: False for field in SUPPORT}, -1, 0)
    with pytest.raises(CounterfactualXrayError, match="cannot exceed"):
        audit_counterfactual_xray_support(plan, {field: False for field in SUPPORT}, 1, 2)


def test_loader_rejects_json_digest_and_shape(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b"bad")
    with pytest.raises(CounterfactualXrayError, match="UTF-8 JSON"):
        load_counterfactual_xray_plan(invalid)
    scalar = tmp_path / "scalar.json"
    scalar.write_text("[]", encoding="utf-8")
    with pytest.raises(CounterfactualXrayError, match="JSON object"):
        load_counterfactual_xray_plan(scalar)
    payload = _payload()
    payload["question"] = "tampered"
    forged = tmp_path / "forged.json"
    forged.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CounterfactualXrayError, match="digest"):
        load_counterfactual_xray_plan(forged)


def test_loader_rejects_identity_perturbation_output_and_causal_drift(tmp_path: Path) -> None:
    def reject(mutate: Callable[[dict[str, object]], None], match: str) -> None:
        payload = _payload()
        mutate(payload)
        with pytest.raises(CounterfactualXrayError, match=match):
            load_counterfactual_xray_plan(_write(tmp_path, payload))

    reject(lambda p: p.update(task_id="R3-346"), "identity")
    reject(lambda p: p.update(perturbation_dimensions=[]), "perturbations")
    reject(lambda p: p.update(required_outputs=[]), "outputs")
    reject(lambda p: p.update(claim_boundary="causal"), "causal boundary")
    reject(lambda p: p.update(perturbation_dimensions="invalid"), "array")


def test_loader_rejects_nested_protocol_lineage_and_execution_drift(tmp_path: Path) -> None:
    def reject(mutate: Callable[[dict[str, object]], None], match: str) -> None:
        payload = _payload()
        mutate(payload)
        with pytest.raises(CounterfactualXrayError, match=match):
            load_counterfactual_xray_plan(_write(tmp_path, payload))

    reject(
        lambda p: p.update(
            provenance_policy={
                **_mapping(p["provenance_policy"]),
                "same_model_and_reference_data": False,
            }
        ),
        "provenance policy",
    )
    reject(
        lambda p: p.update(
            delta_policy={**_mapping(p["delta_policy"]), "invented_composite_score": True}
        ),
        "delta policy",
    )
    reject(
        lambda p: p.update(
            minimality_policy={**_mapping(p["minimality_policy"]), "bounded_domain_only": False}
        ),
        "minimality policy",
    )
    reject(
        lambda p: p.update(
            support_requirements={
                **_mapping(p["support_requirements"]),
                "synthetic_substitution": True,
            }
        ),
        "fail-closed",
    )
    reject(
        lambda p: p.update(
            source_lineage={
                **_mapping(p["source_lineage"]),
                "decision_corpus_records": "0" * 64,
            }
        ),
        "lineage",
    )
    reject(
        lambda p: p.update(
            execution_policy={
                **_mapping(p["execution_policy"]),
                "causal_inference_claim": True,
            }
        ),
        "read-only and non-causal",
    )
    reject(
        lambda p: p.update(
            execution_policy={
                **_mapping(p["execution_policy"]),
                "manifest_changes": "IN_PLACE",
            }
        ),
        "change policy",
    )


def test_loader_rejects_field_sets_and_nested_types(tmp_path: Path) -> None:
    def reject(mutate: Callable[[dict[str, object]], None], match: str) -> None:
        payload = _payload()
        mutate(payload)
        with pytest.raises(CounterfactualXrayError, match=match):
            load_counterfactual_xray_plan(_write(tmp_path, payload))

    reject(lambda p: p.update(unexpected=True), "plan fields")
    reject(lambda p: p.update(study_id="other"), "study identifier")
    reject(lambda p: p.update(question=""), "non-empty text")
    reject(
        lambda p: p.update(provenance_policy={**_mapping(p["provenance_policy"]), "x": 1}),
        "provenance fields",
    )
    reject(
        lambda p: p.update(delta_policy={**_mapping(p["delta_policy"]), "x": 1}),
        "delta fields",
    )
    reject(
        lambda p: p.update(minimality_policy={**_mapping(p["minimality_policy"]), "x": 1}),
        "minimality fields",
    )
    reject(
        lambda p: p.update(support_requirements={**_mapping(p["support_requirements"]), "x": 1}),
        "support requirement fields",
    )
    reject(
        lambda p: p.update(
            support_requirements={
                **_mapping(p["support_requirements"]),
                "required_fields": ["original_decision_summary"],
            }
        ),
        "support fields are not frozen",
    )
    reject(lambda p: p.update(source_lineage={}), "lineage fields")
    reject(
        lambda p: p.update(execution_policy={**_mapping(p["execution_policy"]), "x": 1}),
        "execution fields",
    )
    reject(lambda p: p.update(provenance_policy="invalid"), "must be an object")
    reject(lambda p: p.update(perturbation_dimensions=[1]), "non-empty text")
    reject(
        lambda p: p.update(
            provenance_policy={
                **_mapping(p["provenance_policy"]),
                "same_model_and_reference_data": "yes",
            }
        ),
        "must be boolean",
    )
