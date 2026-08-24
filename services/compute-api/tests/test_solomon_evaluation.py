from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from routemind_compute.application import solomon_evaluation
from routemind_compute.application.public_benchmarks import (
    CanonicalVrptwInstance,
    CanonicalVrptwNode,
    CartesianPoint,
    ParsedPublicBenchmark,
    TransformationRecord,
)
from routemind_compute.application.solomon_evaluation import (
    SolomonEvaluationError,
    SolomonSelection,
    compare_reference,
    load_solomon_protocol,
    run_selected_instance,
    solve_solomon_instance,
    source_manifest,
    summarize_campaign,
    wilson_interval,
)
from routemind_compute.application.verification import PublicVrptwVerificationReport

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = (
    ROOT / "docs" / "research" / "r3" / "manifests" / "solomon" / "solomon-stratified-six-v1.json"
)


def tiny_instance() -> CanonicalVrptwInstance:
    return CanonicalVrptwInstance(
        instance_id="TINY101",
        max_vehicles=2,
        vehicle_capacity=10,
        depot=CanonicalVrptwNode(0, CartesianPoint(0, 0), 0, 0, 100, 0),
        customers=(
            CanonicalVrptwNode(1, CartesianPoint(3, 4), 4, 0, 30, 1),
            CanonicalVrptwNode(2, CartesianPoint(6, 8), 4, 0, 50, 1),
        ),
    )


def parsed_tiny() -> ParsedPublicBenchmark:
    return ParsedPublicBenchmark(
        tiny_instance(),
        "1" * 64,
        "2" * 64,
        (
            TransformationRecord(
                "fixture",
                "SOLOMON_INTEGER_TEXT",
                "CANONICAL_VRPTW_V1_CARTESIAN",
                True,
            ),
        ),
    )


def tiny_selection() -> SolomonSelection:
    return SolomonSelection(
        "C1", "TINY101", "In/tiny101.txt", "tiny.txt", "2" * 64, 1, 20, "REPORTED"
    )


def verification_for(
    vehicles: int, distance: float, *, valid: bool = True
) -> PublicVrptwVerificationReport:
    return PublicVrptwVerificationReport(valid, (), ("check",), vehicles, distance, valid)


def test_frozen_protocol_loads_and_builds_complete_source_lineage() -> None:
    protocol = load_solomon_protocol(PROTOCOL)

    assert protocol.manifest_id == "r3-311-solomon-stratified-six-v1"
    assert tuple(item.family for item in protocol.instances) == (
        "C1",
        "C2",
        "R1",
        "R2",
        "RC1",
        "RC2",
    )
    assert protocol.wall_time_seconds == 10
    assert protocol.threads == 1
    source = source_manifest(protocol, protocol.selection("C101"))
    assert (
        source.artifact.sha256 == "a6da75152d182d60ecd2c6f854296f5be452f92282d096adebcf5d99a7f16516"
    )
    assert source.references[0].vehicle_count == 10
    assert source.redistribution_allowed is False


def test_protocol_rejects_post_result_or_non_stratified_mutation(tmp_path: Path) -> None:
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    payload["material_execution_started"] = True
    mutated = tmp_path / "mutated.json"
    mutated.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SolomonEvaluationError, match="precede material"):
        load_solomon_protocol(mutated)

    payload["material_execution_started"] = False
    payload["selection"]["selected_count"] = 5
    mutated.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SolomonEvaluationError, match="selected_count"):
        load_solomon_protocol(mutated)

    payload["selection"]["selected_count"] = 6
    payload["selection"]["instances"][1]["family"] = "C1"
    mutated.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SolomonEvaluationError, match="families must be unique"):
        load_solomon_protocol(mutated)


def test_protocol_rejects_solver_or_resource_drift(tmp_path: Path) -> None:
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    mutated = tmp_path / "mutated.json"
    payload["solver"]["package"] = "other"
    mutated.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SolomonEvaluationError, match="must be ortools"):
        load_solomon_protocol(mutated)

    payload["solver"]["package"] = "ortools"
    payload["resource_policy"]["threads"] = 2
    mutated.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SolomonEvaluationError, match="one solver thread"):
        load_solomon_protocol(mutated)

    payload["resource_policy"]["threads"] = 1
    payload["solver"]["version"] = "0.0.0"
    mutated.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SolomonEvaluationError, match="installed OR-Tools"):
        load_solomon_protocol(mutated)


def test_tiny_solver_output_passes_independent_verification() -> None:
    frozen = load_solomon_protocol(PROTOCOL)
    protocol = replace(frozen, instances=(tiny_selection(),), wall_time_seconds=0.2)

    run = solve_solomon_instance(
        protocol,
        tiny_selection(),
        parsed_tiny(),
        campaign_id="synthetic-test",
        code_revision="a" * 40,
    )

    assert run.verification is not None
    assert run.verification.valid is True
    assert run.verification.complete is True
    assert run.verification.recomputed_vehicle_count == 1
    assert run.classified.accepted_feasible_incumbent is True
    assert run.solution is not None
    assert {visit.node_id for route in run.solution.routes for visit in route.visits} == {0, 1, 2}
    payload = run.payload()
    assert payload["solver"]["routing_random_seed"] == "SEED_API_NOT_AVAILABLE"  # type: ignore[index]

    with pytest.raises(SolomonEvaluationError, match="full lowercase Git SHA"):
        solve_solomon_instance(
            protocol,
            tiny_selection(),
            parsed_tiny(),
            campaign_id="synthetic-test",
            code_revision="short",
        )


@pytest.mark.parametrize(
    ("vehicles", "valid", "status", "gap"),
    (
        (2, True, "VEHICLE_COUNT_WORSE", None),
        (0, True, "REFERENCE_CONTRADICTION_REVIEW", None),
        (1, True, "COMPARABLE_SAME_VEHICLE_COUNT", 5.0),
        (1, False, "REFERENCE_GAP_NOT_APPLICABLE", None),
    ),
)
def test_reference_comparison_preserves_hierarchy(
    vehicles: int, valid: bool, status: str, gap: float | None
) -> None:
    comparison = compare_reference(tiny_selection(), verification_for(vehicles, 21, valid=valid))

    assert comparison.status == status
    assert comparison.distance_gap_percent == gap


def test_wilson_interval_records_underpowered_gate() -> None:
    lower, upper = wilson_interval(6, 6)

    assert lower == pytest.approx(0.6096657120978346)
    assert upper == pytest.approx(1.0)
    with pytest.raises(SolomonEvaluationError, match="between zero and total"):
        wilson_interval(7, 6)
    with pytest.raises(SolomonEvaluationError, match="positive total"):
        wilson_interval(False, 6)


def test_status_mapping_preserves_timeout_proof_and_failure_semantics() -> None:
    termination = solomon_evaluation._termination

    assert termination("ROUTING_PARTIAL_SUCCESS_LOCAL_OPTIMUM_NOT_REACHED")[0].value == (
        "WALL_TIME_LIMIT"
    )
    assert termination("ROUTING_FAIL_TIMEOUT")[0].value == "WALL_TIME_LIMIT"
    assert termination("ROUTING_OPTIMAL")[1].value == "OPTIMALITY"
    assert termination("ROUTING_INFEASIBLE")[1].value == "INFEASIBILITY"
    assert termination("ROUTING_INVALID")[2] == "ORTOOLS_ROUTING_INVALID"
    assert termination("ROUTING_SUCCESS")[0].value == "COMPLETED"
    assert termination("UNRECOGNIZED")[2] == "ORTOOLS_STATUS_UNKNOWN"


def test_synthetic_instance_runner_writes_immutable_verified_artifact(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "public_benchmarks" / "solomon-tiny.txt"
    raw_fixture = fixture.read_bytes()
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    payload["resource_policy"]["wall_time_seconds_per_instance"] = 0.2
    payload["selection"]["instances"][0].update(
        {
            "instance_id": "TINY101",
            "archive_member": "In/tiny101.txt",
            "relative_path": "datasets/public-benchmarks/solomon/tiny101.txt",
            "sha256": hashlib.sha256(raw_fixture).hexdigest(),
            "reference_vehicle_count": 1,
            "reference_distance": 20.0,
            "reference_status": "REPORTED",
        }
    )
    protocol_path = tmp_path / "synthetic-protocol.json"
    protocol_path.write_text(json.dumps(payload), encoding="utf-8")
    data_root = tmp_path / "data"
    source_path = data_root / "datasets" / "public-benchmarks" / "solomon" / "tiny101.txt"
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(raw_fixture)
    output = data_root / "experiments" / "r3" / "R3-311" / "synthetic-campaign"

    result_path = run_selected_instance(
        protocol_path,
        data_root,
        output,
        "TINY101",
        "synthetic-campaign",
        "c" * 40,
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))

    assert result["verification"]["valid"] is True
    assert result["classification"]["accepted_feasible_incumbent"] is True
    assert result_path.with_suffix(".json.sha256").is_file()
    with pytest.raises(SolomonEvaluationError, match="immutable artifact"):
        run_selected_instance(
            protocol_path,
            data_root,
            output,
            "TINY101",
            "synthetic-campaign",
            "c" * 40,
        )


def test_campaign_summary_verifies_artifact_hashes_and_retains_all_runs(tmp_path: Path) -> None:
    protocol = load_solomon_protocol(PROTOCOL)
    output = tmp_path / protocol.result_relative_root / "campaign"
    output.mkdir(parents=True)
    for index, selected in enumerate(protocol.instances):
        payload = {
            "campaign_id": "campaign",
            "code_revision": "b" * 40,
            "classification": {
                "accepted_feasible_incumbent": index < 5,
                "outcome": "FEASIBLE_INCUMBENT" if index < 5 else "TIMEOUT_NO_FEASIBLE",
            },
        }
        encoded = (json.dumps(payload) + "\n").encode()
        path = output / f"{selected.instance_id.lower()}.json"
        path.write_bytes(encoded)
        path.with_suffix(".json.sha256").write_text(
            hashlib.sha256(encoded).hexdigest(), encoding="ascii"
        )

    summary_path = summarize_campaign(PROTOCOL, tmp_path, output, "campaign", "b" * 40)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert summary["selected_count"] == summary["retained_count"] == 6
    assert summary["verified_complete_count"] == 5
    assert summary["hypothesis_passed"] is False
    assert summary["statistical_disposition"] == "S-FAIL"
    assert summary["outcomes"] == {"FEASIBLE_INCUMBENT": 5, "TIMEOUT_NO_FEASIBLE": 1}
    assert summary_path.with_suffix(".json.sha256").is_file()


def test_campaign_summary_rejects_tampered_artifact(tmp_path: Path) -> None:
    protocol = load_solomon_protocol(PROTOCOL)
    output = tmp_path / protocol.result_relative_root / "campaign"
    output.mkdir(parents=True)
    selected = protocol.instances[0]
    path = output / f"{selected.instance_id.lower()}.json"
    path.write_text("{}", encoding="utf-8")
    path.with_suffix(".json.sha256").write_text("0" * 64, encoding="ascii")

    with pytest.raises(SolomonEvaluationError, match="checksum mismatch"):
        summarize_campaign(PROTOCOL, tmp_path, output, "campaign", "b" * 40)


def test_cli_routes_instance_and_summary_actions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    instance_path = tmp_path / "instance.json"
    summary_path = tmp_path / "summary.json"

    def fake_instance(*_args: object) -> Path:
        return instance_path

    def fake_summary(*_args: object) -> Path:
        return summary_path

    monkeypatch.setattr(solomon_evaluation, "run_selected_instance", fake_instance)
    monkeypatch.setattr(solomon_evaluation, "summarize_campaign", fake_summary)
    common = [
        "--protocol",
        str(PROTOCOL),
        "--data-root",
        str(tmp_path),
        "--output-directory",
        str(tmp_path / "out"),
        "--campaign-id",
        "campaign",
        "--code-revision",
        "d" * 40,
    ]

    assert solomon_evaluation.main(["instance", *common, "--instance-id", "C101"]) == 0
    assert str(instance_path) in capsys.readouterr().out
    assert solomon_evaluation.main(["summarize", *common]) == 0
    assert str(summary_path) in capsys.readouterr().out
    with pytest.raises(SolomonEvaluationError, match="requires --instance-id"):
        solomon_evaluation.main(["instance", *common])
    with pytest.raises(SolomonEvaluationError, match="does not accept"):
        solomon_evaluation.main(["summarize", *common, "--instance-id", "C101"])
