from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from zipfile import ZipFile

import pytest

from routemind_compute.application import homberger_evaluation
from routemind_compute.application.artifacts import DataRootArtifactAdapter
from routemind_compute.application.homberger_evaluation import (
    HombergerArchive,
    HombergerEvaluationError,
    HombergerSelection,
    compare_reference,
    load_homberger_protocol,
    run_selected_instance,
    solve_homberger_instance,
    source_manifest,
    summarize_campaign,
    verify_selected_archive,
)
from routemind_compute.application.public_benchmarks import (
    CanonicalVrptwInstance,
    CanonicalVrptwNode,
    CartesianPoint,
    ParsedPublicBenchmark,
    TransformationRecord,
)
from routemind_compute.application.verification import PublicVrptwVerificationReport

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = (
    ROOT
    / "docs"
    / "research"
    / "r3"
    / "manifests"
    / "gehring-homberger"
    / "scale-first-replicates-v1.json"
)


def tiny_instance(instance_id: str = "C1_2_1") -> CanonicalVrptwInstance:
    return CanonicalVrptwInstance(
        instance_id=instance_id,
        max_vehicles=2,
        vehicle_capacity=10,
        depot=CanonicalVrptwNode(0, CartesianPoint(0, 0), 0, 0, 100, 0),
        customers=(
            CanonicalVrptwNode(1, CartesianPoint(3, 4), 4, 0, 30, 1),
            CanonicalVrptwNode(2, CartesianPoint(6, 8), 4, 0, 50, 1),
        ),
    )


def parsed_tiny(instance_id: str = "C1_2_1") -> ParsedPublicBenchmark:
    return ParsedPublicBenchmark(
        tiny_instance(instance_id),
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


def verification_for(
    vehicles: int, distance: float, *, valid: bool = True
) -> PublicVrptwVerificationReport:
    return PublicVrptwVerificationReport(valid, (), ("check",), vehicles, distance, valid)


def test_frozen_protocol_loads_exact_scale_family_census_and_lineage() -> None:
    protocol = load_homberger_protocol(PROTOCOL)

    assert protocol.manifest_id == "r3-312-gh-scale-first-replicates-v1"
    assert protocol.manifest_sha256 == hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    assert len(protocol.source.archives) == 5
    assert len(protocol.instances) == 30
    assert {item.customer_count for item in protocol.instances} == {200, 400, 600, 800, 1000}
    assert all(item.instance_id.endswith("_1") for item in protocol.instances)
    assert sum(item.reference_comparison_allowed for item in protocol.instances) == 24
    assert protocol.wall_time_seconds == 5
    assert protocol.threads == 1

    selected = protocol.selection("C1_2_1")
    source = source_manifest(protocol, selected)
    assert source.artifact.sha256 == selected.sha256
    assert source.distribution_sha256 == protocol.source.archive(200).sha256
    assert source.references[0].vehicle_count == 20
    assert source.redistribution_allowed is False
    questioned = source_manifest(protocol, protocol.selection("C1_4_1"))
    assert "questions whether" in questioned.references[0].notes


def test_protocol_rejects_post_result_selection_and_reference_quality_mutation(
    tmp_path: Path,
) -> None:
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    mutated = tmp_path / "mutated.json"
    payload["material_execution_started"] = True
    mutated.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(HombergerEvaluationError, match="precede material"):
        load_homberger_protocol(mutated)

    payload["material_execution_started"] = False
    payload["selection"]["selected_count"] = 29
    mutated.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(HombergerEvaluationError, match="exactly 30"):
        load_homberger_protocol(mutated)

    payload["selection"]["selected_count"] = 30
    payload["selection"]["instances"][0]["instance_id"] = "C1_2_2"
    mutated.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(HombergerEvaluationError, match="first-replicate"):
        load_homberger_protocol(mutated)

    payload["selection"]["instances"][0]["instance_id"] = "C1_2_1"
    withheld = next(
        item
        for item in payload["selection"]["instances"]
        if not item["reference_comparison_allowed"]
    )
    del withheld["reference_note"]
    mutated.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(HombergerEvaluationError, match="requires a source note"):
        load_homberger_protocol(mutated)


@pytest.mark.parametrize(
    ("mutation_path", "value", "message"),
    (
        (("solver", "package"), "other", "must be ortools"),
        (("solver", "threads"), 2, "one solver thread"),
        (("resource_policy", "maximum_instances"), 29, "maximum_instances"),
        (("resource_policy", "process_isolation"), "SHARED", "isolated process"),
        (("verification", "verifier_revision"), "other", "R3-314"),
        (("analysis_plan", "statistical_disposition"), "S-PASS", "S-NOT-APPLICABLE"),
    ),
)
def test_protocol_rejects_solver_resource_or_analysis_drift(
    tmp_path: Path,
    mutation_path: tuple[str, str],
    value: object,
    message: str,
) -> None:
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    payload[mutation_path[0]][mutation_path[1]] = value
    mutated = tmp_path / "mutated.json"
    mutated.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(HombergerEvaluationError, match=message):
        load_homberger_protocol(mutated)


@pytest.mark.parametrize(
    ("path", "value", "message"),
    (
        (("schema_version",), "other", "schema is unsupported"),
        (("frozen_against_revision",), "short", "frozen revision"),
        (("source", "archives"), [], "five frozen scales"),
        (("selection", "customer_counts"), [200], "customer counts"),
        (("selection", "structural_families"), ["C1"], "six families"),
        (("selection", "instances", 1, "family"), "C1", "census order"),
        (("selection", "instances", 1, "instance_id"), "C1_2_1", "identities"),
        (("resource_policy", "wall_time_seconds_per_instance"), 0, "must be positive"),
        (
            ("resource_policy", "maximum_campaign_solver_wall_time_seconds"),
            149,
            "per-instance bound",
        ),
        (("verification", "outcome_contract_revision"), "other", "R3-317"),
        (("solver", "version"), "0.0.0", "installed OR-Tools"),
        (("artifact_policy", "result_relative_root"), "../escape", "safe relative"),
        (("selection", "instances", 0, "reference_distance"), 0, "distance must be positive"),
        (("selection", "instances", 0, "reference_note"), "", "must be non-blank"),
    ),
)
def test_additional_protocol_integrity_guards(
    tmp_path: Path,
    path: tuple[str | int, ...],
    value: object,
    message: str,
) -> None:
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    target: object = payload
    for part in path[:-1]:
        target = target[part]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]
    mutated = tmp_path / "mutated.json"
    mutated.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(HombergerEvaluationError, match=message):
        load_homberger_protocol(mutated)


def test_protocol_rejects_unreadable_json_and_unknown_selection(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    with pytest.raises(HombergerEvaluationError, match="unreadable"):
        load_homberger_protocol(malformed)

    protocol = load_homberger_protocol(PROTOCOL)
    with pytest.raises(HombergerEvaluationError, match="not uniquely selected"):
        protocol.selection("UNKNOWN")
    with pytest.raises(HombergerEvaluationError, match="no unique source archive"):
        protocol.source.archive(300)


def test_selected_archive_verifies_archive_and_member_hashes(tmp_path: Path) -> None:
    protocol = load_homberger_protocol(PROTOCOL)
    selected = protocol.selection("C1_2_1")
    archive_relative = "datasets/public-benchmarks/gehring-homberger/200/source.zip"
    archive_path = tmp_path / archive_relative
    archive_path.parent.mkdir(parents=True)
    member = b"frozen-member"
    with ZipFile(archive_path, "w") as bundle:
        bundle.writestr(selected.archive_member, member)
    archive = HombergerArchive(
        200,
        protocol.source.archive(200).source_page_url,
        protocol.source.archive(200).download_url,
        archive_relative,
        archive_path.stat().st_size,
        hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        1,
    )
    synthetic = replace(
        protocol,
        source=replace(protocol.source, archives=(archive,)),
        instances=(replace(selected, sha256=hashlib.sha256(member).hexdigest()),),
    )

    verify_selected_archive(synthetic, synthetic.instances[0], DataRootArtifactAdapter(tmp_path))

    invalid = replace(synthetic, instances=(replace(synthetic.instances[0], sha256="0" * 64),))
    with pytest.raises(HombergerEvaluationError, match="member checksum"):
        verify_selected_archive(invalid, invalid.instances[0], DataRootArtifactAdapter(tmp_path))


@pytest.mark.parametrize(
    ("case", "message"),
    (
        ("bytes", "byte count"),
        ("members", "member count"),
        ("missing", "not unique"),
        ("bad_zip", "cannot be verified"),
    ),
)
def test_selected_archive_rejects_structural_corruption(
    tmp_path: Path, case: str, message: str
) -> None:
    protocol = load_homberger_protocol(PROTOCOL)
    selected = protocol.selection("C1_2_1")
    relative = "datasets/public-benchmarks/gehring-homberger/200/corrupt.zip"
    archive_path = tmp_path / relative
    archive_path.parent.mkdir(parents=True)
    member = b"member"
    if case == "bad_zip":
        archive_path.write_bytes(b"not-a-zip")
        actual_members = 1
    else:
        with ZipFile(archive_path, "w") as bundle:
            if case == "missing":
                bundle.writestr("OTHER.TXT", member)
            else:
                bundle.writestr(selected.archive_member, member)
                if case == "members":
                    bundle.writestr("OTHER.TXT", b"other")
        actual_members = 1
    archive = HombergerArchive(
        200,
        protocol.source.archive(200).source_page_url,
        protocol.source.archive(200).download_url,
        relative,
        archive_path.stat().st_size + (1 if case == "bytes" else 0),
        hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        actual_members,
    )
    synthetic = replace(
        protocol,
        source=replace(protocol.source, archives=(archive,)),
        instances=(replace(selected, sha256=hashlib.sha256(member).hexdigest()),),
    )

    with pytest.raises(HombergerEvaluationError, match=message):
        verify_selected_archive(
            synthetic, synthetic.instances[0], DataRootArtifactAdapter(tmp_path)
        )


def test_tiny_solver_output_passes_independent_verification() -> None:
    frozen = load_homberger_protocol(PROTOCOL)
    selected = frozen.selection("C1_2_1")
    protocol = replace(frozen, instances=(selected,), wall_time_seconds=0.2)

    run = solve_homberger_instance(
        protocol,
        selected,
        parsed_tiny(),
        campaign_id="synthetic-test",
        code_revision="a" * 40,
    )

    assert run.verification is not None
    assert run.verification.valid is True
    assert run.verification.complete is True
    assert run.classified.accepted_feasible_incumbent is True
    assert run.payload()["instance"]["customer_count"] == 200  # type: ignore[index]
    with pytest.raises(HombergerEvaluationError, match="full lowercase Git SHA"):
        solve_homberger_instance(
            protocol,
            selected,
            parsed_tiny(),
            campaign_id="synthetic-test",
            code_revision="short",
        )


def test_memory_error_is_retained_as_resource_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = load_homberger_protocol(PROTOCOL)
    selected = protocol.selection("C1_2_1")

    def fail_for_memory(*_args: object, **_kwargs: object) -> None:
        raise MemoryError

    monkeypatch.setattr(homberger_evaluation, "solve_canonical_vrptw", fail_for_memory)
    run = solve_homberger_instance(
        protocol,
        selected,
        parsed_tiny(),
        campaign_id="synthetic-memory",
        code_revision="b" * 40,
    )

    assert run.ortools_status == "PROCESS_MEMORY_LIMIT"
    assert run.classified.outcome.value == "RESOURCE_LIMIT_NO_FEASIBLE"
    assert [item.value for item in run.classified.limit_events] == ["MEMORY"]


@pytest.mark.parametrize(
    ("status", "termination", "proof", "failure"),
    (
        ("ROUTING_FAIL_TIMEOUT", "WALL_TIME_LIMIT", "NONE", None),
        ("ROUTING_OPTIMAL", "COMPLETED", "OPTIMALITY", None),
        ("ROUTING_INFEASIBLE", "COMPLETED", "INFEASIBILITY", None),
        ("ROUTING_INVALID", "ERROR", "NONE", "ORTOOLS_ROUTING_INVALID"),
        ("ROUTING_SUCCESS", "COMPLETED", "NONE", None),
        ("UNKNOWN", "ERROR", "NONE", "ORTOOLS_STATUS_UNKNOWN"),
    ),
)
def test_routing_status_mapping_is_semantically_explicit(
    status: str, termination: str, proof: str, failure: str | None
) -> None:
    observed_termination, observed_proof, observed_failure = (
        homberger_evaluation._routing_termination(status)
    )

    assert observed_termination.value == termination
    assert observed_proof.value == proof
    assert observed_failure == failure


def test_null_payloads_and_instance_mismatch_are_explicit() -> None:
    assert homberger_evaluation._solution_payload(None) is None
    assert homberger_evaluation._verification_payload(None) is None
    protocol = load_homberger_protocol(PROTOCOL)
    selected = protocol.selection("C1_2_1")
    with pytest.raises(HombergerEvaluationError, match="parsed instance"):
        solve_homberger_instance(
            protocol,
            selected,
            parsed_tiny("OTHER"),
            campaign_id="synthetic-test",
            code_revision="a" * 40,
        )


@pytest.mark.parametrize(
    ("instance_id", "vehicles", "valid", "status", "gap"),
    (
        ("C1_2_1", 21, True, "VEHICLE_COUNT_WORSE", None),
        ("C1_2_1", 19, True, "REFERENCE_CONTRADICTION_REVIEW", None),
        ("C1_2_1", 20, True, "COMPARABLE_SAME_VEHICLE_COUNT", 1.0),
        ("C1_2_1", 20, False, "REFERENCE_GAP_NOT_APPLICABLE", None),
        ("C1_4_1", 40, True, "REFERENCE_QUALITY_REVIEW", None),
    ),
)
def test_reference_comparison_preserves_hierarchy_and_quality_guard(
    instance_id: str,
    vehicles: int,
    valid: bool,
    status: str,
    gap: float | None,
) -> None:
    protocol = load_homberger_protocol(PROTOCOL)
    selected = protocol.selection(instance_id)
    distance = selected.reference_distance * 1.01

    comparison = compare_reference(selected, verification_for(vehicles, distance, valid=valid))

    assert comparison.status == status
    if gap is None:
        assert comparison.distance_gap_percent is None
    else:
        assert comparison.distance_gap_percent == pytest.approx(gap, abs=0.001)
    if not selected.reference_comparison_allowed:
        assert comparison.reference_note is not None


def test_synthetic_runner_writes_immutable_verified_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    protocol = load_homberger_protocol(PROTOCOL)
    output = tmp_path / protocol.result_relative_root / "synthetic-campaign"
    monkeypatch.setattr(homberger_evaluation, "verify_selected_archive", lambda *_args: None)
    monkeypatch.setattr(homberger_evaluation, "load_public_benchmark", lambda *_args: parsed_tiny())

    result_path = run_selected_instance(
        PROTOCOL,
        tmp_path,
        output,
        "C1_2_1",
        "synthetic-campaign",
        "c" * 40,
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))

    assert result["verification"]["valid"] is True
    assert result["classification"]["accepted_feasible_incumbent"] is True
    assert result_path.with_suffix(".json.sha256").is_file()
    with pytest.raises(HombergerEvaluationError, match="immutable artifact"):
        run_selected_instance(
            PROTOCOL,
            tmp_path,
            output,
            "C1_2_1",
            "synthetic-campaign",
            "c" * 40,
        )


def _write_summary_fixture(
    output: Path,
    protocol_sha256: str,
    selection: HombergerSelection,
    *,
    accepted: bool,
) -> None:
    payload = {
        "schema_version": "routemind-homberger-run-v1",
        "campaign_id": "campaign",
        "code_revision": "d" * 40,
        "manifest_id": "r3-312-gh-scale-first-replicates-v1",
        "manifest_sha256": protocol_sha256,
        "instance": {
            "customer_count": selection.customer_count,
            "family": selection.family,
            "instance_id": selection.instance_id,
            "archive_member": selection.archive_member,
            "artifact_sha256": selection.sha256,
        },
        "solver": {"elapsed_seconds": 1.5},
        "classification": {
            "accepted_feasible_incumbent": accepted,
            "outcome": "TIMEOUT_WITH_FEASIBLE" if accepted else "TIMEOUT_NO_FEASIBLE",
            "verification_issue_codes": [],
        },
        "reference_comparison": {
            "status": (
                "COMPARABLE_SAME_VEHICLE_COUNT"
                if accepted and selection.reference_comparison_allowed
                else "REFERENCE_QUALITY_REVIEW"
                if not selection.reference_comparison_allowed
                else "REFERENCE_GAP_NOT_APPLICABLE"
            ),
            "comparison_allowed": selection.reference_comparison_allowed,
            "reference_vehicle_count": selection.reference_vehicle_count,
            "reference_distance": selection.reference_distance,
            "reference_note": selection.reference_note,
            "distance_gap_percent": (
                2.5 if accepted and selection.reference_comparison_allowed else None
            ),
        },
    }
    encoded = (json.dumps(payload) + "\n").encode()
    path = output / f"{selection.instance_id.lower()}.json"
    path.write_bytes(encoded)
    path.with_suffix(".json.sha256").write_text(
        hashlib.sha256(encoded).hexdigest(), encoding="ascii"
    )


def _write_all_summary_fixtures(output: Path) -> None:
    protocol = load_homberger_protocol(PROTOCOL)
    output.mkdir(parents=True)
    for selected in protocol.instances:
        _write_summary_fixture(output, protocol.manifest_sha256, selected, accepted=True)


def test_campaign_summary_retains_all_results_and_labels_each_scale(tmp_path: Path) -> None:
    protocol = load_homberger_protocol(PROTOCOL)
    output = tmp_path / protocol.result_relative_root / "campaign"
    output.mkdir(parents=True)
    for selected in protocol.instances:
        accepted = selected.customer_count == 200 or (
            selected.customer_count == 400 and selected.family in {"C1", "C2", "R1"}
        )
        _write_summary_fixture(
            output,
            protocol.manifest_sha256,
            selected,
            accepted=accepted,
        )

    summary_path = summarize_campaign(PROTOCOL, tmp_path, output, "campaign", "d" * 40)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert summary["selected_count"] == summary["retained_count"] == 30
    assert summary["verified_complete_count"] == 9
    assert summary["statistical_disposition"] == "S-NOT-APPLICABLE"
    labels = {item["customer_count"]: item["support_label"] for item in summary["scales"]}
    assert labels == {
        200: "SUPPORTED_UNDER_FROZEN_POLICY",
        400: "DEGRADED_UNDER_FROZEN_POLICY",
        600: "NO_VERIFIED_INCUMBENT_UNDER_FROZEN_POLICY",
        800: "NO_VERIFIED_INCUMBENT_UNDER_FROZEN_POLICY",
        1000: "NO_VERIFIED_INCUMBENT_UNDER_FROZEN_POLICY",
    }
    assert summary_path.with_suffix(".json.sha256").is_file()


def test_campaign_summary_rejects_tampered_or_misidentified_artifact(tmp_path: Path) -> None:
    protocol = load_homberger_protocol(PROTOCOL)
    output = tmp_path / protocol.result_relative_root / "campaign"
    output.mkdir(parents=True)
    selected = protocol.instances[0]
    _write_summary_fixture(output, protocol.manifest_sha256, selected, accepted=True)
    path = output / f"{selected.instance_id.lower()}.json"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(HombergerEvaluationError, match="checksum mismatch"):
        summarize_campaign(PROTOCOL, tmp_path, output, "campaign", "d" * 40)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("schema_version", "other", "schema mismatch"),
        ("campaign_id", "other", "campaign identity"),
        ("code_revision", "e" * 40, "code revision mismatch"),
        ("manifest_id", "other", "manifest identity"),
        ("manifest_sha256", "0" * 64, "manifest identity"),
        ("instance.instance_id", "OTHER", "selected identity"),
        ("instance.archive_member", "OTHER.TXT", "selected identity"),
        ("instance.artifact_sha256", "0" * 64, "selected identity"),
        ("reference_comparison.reference_distance", 1.0, "reference lineage"),
        ("reference_comparison.comparison_allowed", False, "reference lineage"),
    ),
)
def test_campaign_summary_binds_every_artifact_identity(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    protocol = load_homberger_protocol(PROTOCOL)
    output = tmp_path / protocol.result_relative_root / "campaign"
    _write_all_summary_fixtures(output)
    selected = protocol.instances[0]
    path = output / f"{selected.instance_id.lower()}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "." in field:
        parent, child = field.split(".", 1)
        payload[parent][child] = value
    else:
        payload[field] = value
    encoded = (json.dumps(payload) + "\n").encode()
    path.write_bytes(encoded)
    path.with_suffix(".json.sha256").write_text(
        hashlib.sha256(encoded).hexdigest(), encoding="ascii"
    )

    with pytest.raises(HombergerEvaluationError, match=message):
        summarize_campaign(PROTOCOL, tmp_path, output, "campaign", "d" * 40)


def test_campaign_summary_rejects_scalar_gap_for_withheld_reference(tmp_path: Path) -> None:
    protocol = load_homberger_protocol(PROTOCOL)
    output = tmp_path / protocol.result_relative_root / "campaign"
    _write_all_summary_fixtures(output)
    selected = protocol.selection("C1_4_1")
    path = output / f"{selected.instance_id.lower()}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["reference_comparison"]["distance_gap_percent"] = 1.0
    encoded = (json.dumps(payload) + "\n").encode()
    path.write_bytes(encoded)
    path.with_suffix(".json.sha256").write_text(
        hashlib.sha256(encoded).hexdigest(), encoding="ascii"
    )

    with pytest.raises(HombergerEvaluationError, match="cannot receive a scalar gap"):
        summarize_campaign(PROTOCOL, tmp_path, output, "campaign", "d" * 40)


def test_scalar_gap_requires_same_vehicle_status() -> None:
    protocol = load_homberger_protocol(PROTOCOL)
    selected = protocol.selection("C1_2_1")
    result = {
        "reference_comparison": {
            "status": "VEHICLE_COUNT_WORSE",
            "comparison_allowed": True,
            "reference_vehicle_count": selected.reference_vehicle_count,
            "reference_distance": selected.reference_distance,
            "reference_note": None,
            "distance_gap_percent": 1.0,
        }
    }

    with pytest.raises(HombergerEvaluationError, match="same-vehicle comparison"):
        homberger_evaluation._validate_reference_comparison(result, selected)

    del result["reference_comparison"]["reference_note"]
    with pytest.raises(HombergerEvaluationError, match="reference lineage"):
        homberger_evaluation._validate_reference_comparison(result, selected)


def test_campaign_summary_rejects_invalid_revision_and_incomplete_scale(tmp_path: Path) -> None:
    protocol = load_homberger_protocol(PROTOCOL)
    output = tmp_path / protocol.result_relative_root / "campaign"
    with pytest.raises(HombergerEvaluationError, match="full lowercase Git SHA"):
        summarize_campaign(PROTOCOL, tmp_path, output, "campaign", "short")
    with pytest.raises(HombergerEvaluationError, match="all six structural families"):
        homberger_evaluation._scale_summary(200, [])


def test_output_and_low_level_protocol_boundaries_are_rejected(tmp_path: Path) -> None:
    protocol = load_homberger_protocol(PROTOCOL)
    with pytest.raises(HombergerEvaluationError, match="below the frozen data root"):
        homberger_evaluation._validated_output_directory(protocol, tmp_path, tmp_path / "other")
    with pytest.raises(HombergerEvaluationError, match="distinct campaign"):
        homberger_evaluation._validated_output_directory(
            protocol, tmp_path, tmp_path / protocol.result_relative_root
        )
    with pytest.raises(HombergerEvaluationError, match="unreadable"):
        homberger_evaluation._read_verified_artifact(tmp_path / "missing.json")

    invalid_calls: tuple[Callable[[], object], ...] = (
        lambda: homberger_evaluation._mapping([], "value"),
        lambda: homberger_evaluation._sequence({}, "value"),
        lambda: homberger_evaluation._required({}, "value"),
        lambda: homberger_evaluation._string({"value": ""}, "value"),
        lambda: homberger_evaluation._safe_relative_path({"value": "../bad"}, "value"),
        lambda: homberger_evaluation._boolean({"value": 1}, "value"),
        lambda: homberger_evaluation._integer({"value": True}, "value"),
        lambda: homberger_evaluation._positive_integer({"value": 0}, "value"),
        lambda: homberger_evaluation._number({"value": float("nan")}, "value"),
        lambda: homberger_evaluation._digest({"value": "bad"}, "value"),
        lambda: homberger_evaluation._integer_array({"value": [True]}, "value"),
        lambda: homberger_evaluation._string_array({"value": [""]}, "value"),
    )
    for invalid_call in invalid_calls:
        with pytest.raises(HombergerEvaluationError):
            invalid_call()


def test_cli_routes_instance_and_summary_actions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    instance_path = tmp_path / "instance.json"
    summary_path = tmp_path / "summary.json"
    monkeypatch.setattr(homberger_evaluation, "run_selected_instance", lambda *_args: instance_path)
    monkeypatch.setattr(homberger_evaluation, "summarize_campaign", lambda *_args: summary_path)
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
        "e" * 40,
    ]

    assert homberger_evaluation.main(["instance", *common, "--instance-id", "C1_2_1"]) == 0
    assert str(instance_path) in capsys.readouterr().out
    assert homberger_evaluation.main(["summarize", *common]) == 0
    assert str(summary_path) in capsys.readouterr().out
    with pytest.raises(HombergerEvaluationError, match="requires --instance-id"):
        homberger_evaluation.main(["instance", *common])
    with pytest.raises(HombergerEvaluationError, match="does not accept"):
        homberger_evaluation.main(["summarize", *common, "--instance-id", "C1_2_1"])
