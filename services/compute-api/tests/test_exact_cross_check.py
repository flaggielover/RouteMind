from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from routemind_compute.application import exact_cross_check
from routemind_compute.application.exact_cross_check import (
    ExactCrossCheckError,
    ExactProtocol,
    ExactSelection,
    compare_candidate,
    derive_prefix_instance,
    enumerate_feasible_routes,
    execute_cross_check,
    load_exact_protocol,
    main,
    run_selected_instance,
    solve_exact_set_partition,
    summarize_campaign,
)
from routemind_compute.application.public_benchmarks import (
    CanonicalVrptwInstance,
    CanonicalVrptwNode,
    CartesianPoint,
    ParsedPublicBenchmark,
    TransformationRecord,
)
from routemind_compute.application.solomon_evaluation import (
    CanonicalRoutingRun,
    load_solomon_protocol,
)
from routemind_compute.application.verification import verify_public_vrptw_solution

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = (
    ROOT
    / "docs"
    / "research"
    / "r3"
    / "manifests"
    / "exact-cross-check"
    / "solomon-prefix-eight-exact-v1.json"
)
SOURCE_PROTOCOL = (
    ROOT / "docs" / "research" / "r3" / "manifests" / "solomon" / "solomon-stratified-six-v1.json"
)


def tiny_instance(
    *,
    instance_id: str = "TINY101",
    capacity: float = 10,
    customer_count: int = 2,
) -> CanonicalVrptwInstance:
    customers = tuple(
        CanonicalVrptwNode(
            index,
            CartesianPoint(index * 3, index * 4),
            1,
            0,
            80,
            1,
        )
        for index in range(1, customer_count + 1)
    )
    return CanonicalVrptwInstance(
        instance_id=instance_id,
        max_vehicles=customer_count,
        vehicle_capacity=capacity,
        depot=CanonicalVrptwNode(0, CartesianPoint(0, 0), 0, 0, 100, 0),
        customers=customers,
    )


def parsed(
    instance: CanonicalVrptwInstance, artifact_sha256: str = "2" * 64
) -> ParsedPublicBenchmark:
    return ParsedPublicBenchmark(
        instance,
        "1" * 64,
        artifact_sha256,
        (
            TransformationRecord(
                "fixture",
                "SOLOMON_INTEGER_TEXT",
                "CANONICAL_VRPTW_V1_CARTESIAN",
                True,
            ),
        ),
    )


def protocol_for(selection: ExactSelection, customer_count: int = 2) -> ExactProtocol:
    return ExactProtocol(
        manifest_id="test-exact",
        manifest_sha256="3" * 64,
        source_protocol_sha256="4" * 64,
        selections=(selection,),
        customer_count=customer_count,
        integer_scale=1000,
        candidate_wall_time_seconds=0.1,
        exact_wall_time_seconds=2,
        threads=1,
        seed=0,
        enumeration_sequence_ceiling=109600,
        result_relative_root="experiments/r3/R3-315",
    )


def test_frozen_protocol_loads_with_expected_identity_and_bounds() -> None:
    protocol = load_exact_protocol(PROTOCOL)

    assert protocol.manifest_id == "r3-315-solomon-prefix-eight-exact-v1"
    assert protocol.manifest_sha256 == hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    assert protocol.manifest_sha256 == (
        "18785fe80e9f4f05490e9c06cf89c12d3457bab539e4dee4518ab8dc05f43e55"
    )
    assert protocol.customer_count == 8
    assert protocol.exact_wall_time_seconds == 30
    assert protocol.enumeration_sequence_ceiling == 109600
    assert protocol.selection("rc201").derived_instance_id == "RC201-PREFIX-08"
    with pytest.raises(ExactCrossCheckError, match="not uniquely selected"):
        protocol.selection("missing")


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda value: value.update(material_execution_started=True), "precede material"),
        (lambda value: value.update(schema_version="unknown"), "schema is unsupported"),
        (
            lambda value: value["selection"].update(selected_count=5),
            "exactly six",
        ),
        (
            lambda value: value["exact_reference_solver"].update(version="0.0"),
            "exact OR-Tools version",
        ),
        (
            lambda value: value["exact_reference_solver"].update(required_proof_status="FEASIBLE"),
            "requires an OPTIMAL",
        ),
        (
            lambda value: value["selection"]["instances"][1].update(source_instance_id="C101"),
            "identities must be unique",
        ),
        (
            lambda value: value["candidate_solver"].update(threads=2),
            "requires one thread",
        ),
        (
            lambda value: value["candidate_solver"].update(sat_random_seed=1),
            "seed policies differ",
        ),
    ],
)
def test_protocol_rejects_frozen_contract_drift(
    tmp_path: Path, mutator: object, message: str
) -> None:
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert callable(mutator)
    mutator(payload)
    path = tmp_path / "mutated.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ExactCrossCheckError, match=message):
        load_exact_protocol(path)


def test_prefix_derivation_is_deterministic_and_preserves_semantics() -> None:
    source = tiny_instance(instance_id="SRC", customer_count=9)
    selection = ExactSelection("C1", "SRC", "SRC-PREFIX-08", "2" * 64)

    derived = derive_prefix_instance(parsed(source), selection, 8)

    assert derived.instance_id == "SRC-PREFIX-08"
    assert tuple(node.node_id for node in derived.customers) == tuple(range(1, 9))
    assert derived.max_vehicles == 8
    assert derived.vehicle_capacity == source.vehicle_capacity
    assert derived.objective_semantics == source.objective_semantics

    with pytest.raises(ExactCrossCheckError, match="identity"):
        derive_prefix_instance(parsed(source), replace(selection, source_instance_id="OTHER"), 8)
    with pytest.raises(ExactCrossCheckError, match="artifact hash"):
        derive_prefix_instance(parsed(source), replace(selection, source_sha256="9" * 64), 8)
    with pytest.raises(ExactCrossCheckError, match="too few"):
        derive_prefix_instance(parsed(source), selection, 10)


def test_enumeration_covers_all_ordered_subsets_and_respects_capacity() -> None:
    roomy = enumerate_feasible_routes(tiny_instance(), scale=1000, sequence_ceiling=4)

    assert roomy.complete is True
    assert roomy.examined_sequences == 4
    assert {column.customer_ids for column in roomy.columns} == {(1,), (2,), (1, 2), (2, 1)}
    assert {column.customer_mask for column in roomy.columns} == {1, 2, 3}

    constrained = enumerate_feasible_routes(
        tiny_instance(capacity=1), scale=1000, sequence_ceiling=4
    )
    assert constrained.examined_sequences == 4
    assert tuple(column.customer_ids for column in constrained.columns) == ((1,), (2,))

    with pytest.raises(ExactCrossCheckError, match="sequence ceiling"):
        enumerate_feasible_routes(tiny_instance(), scale=1000, sequence_ceiling=3)
    with pytest.raises(ExactCrossCheckError, match="must be positive"):
        enumerate_feasible_routes(tiny_instance(), scale=0, sequence_ceiling=4)


def test_exact_set_partition_proves_and_independently_verifies_optimum() -> None:
    instance = tiny_instance()
    enumeration = enumerate_feasible_routes(instance, scale=1000, sequence_ceiling=4)

    result = solve_exact_set_partition(
        instance,
        enumeration,
        scale=1000,
        wall_time_seconds=2,
        threads=1,
        seed=0,
    )

    assert result.status == "OPTIMAL"
    assert result.objective_value == result.best_objective_bound
    assert result.ground_truth_status == "TRANSFORMED_MODEL_GROUND_TRUTH"
    assert result.verification is not None and result.verification.valid
    assert len(result.selected_columns) == 1
    assert sum(column.transformed_distance for column in result.selected_columns) == 20000

    with pytest.raises(ExactCrossCheckError, match="incomplete enumeration"):
        solve_exact_set_partition(
            instance,
            replace(enumeration, complete=False),
            scale=1000,
            wall_time_seconds=2,
            threads=1,
            seed=0,
        )
    with pytest.raises(ExactCrossCheckError, match="limits are invalid"):
        solve_exact_set_partition(
            instance,
            enumeration,
            scale=1000,
            wall_time_seconds=0,
            threads=1,
            seed=0,
        )


def test_exact_path_retains_infeasibility_and_rejects_non_integer_source_values() -> None:
    impossible_customer = CanonicalVrptwNode(1, CartesianPoint(10, 0), 1, 0, 1, 0)
    impossible = CanonicalVrptwInstance(
        "IMPOSSIBLE",
        1,
        1,
        CanonicalVrptwNode(0, CartesianPoint(0, 0), 0, 0, 100, 0),
        (impossible_customer,),
    )
    enumeration = enumerate_feasible_routes(impossible, scale=1000, sequence_ceiling=1)
    assert enumeration.columns == ()
    result = solve_exact_set_partition(
        impossible,
        enumeration,
        scale=1000,
        wall_time_seconds=1,
        threads=1,
        seed=0,
    )
    assert result.status == "INFEASIBLE"
    assert result.solution is None
    assert result.verification is None
    assert result.ground_truth_status == "OPTIMALITY_NOT_PROVEN"

    fractional_time = replace(
        impossible,
        customers=(replace(impossible_customer, service_time=0.0005),),
    )
    with pytest.raises(ExactCrossCheckError, match="cannot be represented"):
        enumerate_feasible_routes(fractional_time, scale=1000, sequence_ceiling=1)
    with pytest.raises(ExactCrossCheckError, match="must be an integer"):
        enumerate_feasible_routes(
            replace(impossible, vehicle_capacity=1.5), scale=1000, sequence_ceiling=1
        )


def test_candidate_comparison_preserves_hierarchical_gap_semantics() -> None:
    instance = tiny_instance()
    enumeration = enumerate_feasible_routes(instance, scale=1000, sequence_ceiling=4)
    exact = solve_exact_set_partition(
        instance, enumeration, scale=1000, wall_time_seconds=2, threads=1, seed=0
    )
    exact_solution = exact.solution
    assert exact_solution is not None
    exact_candidate = CanonicalRoutingRun(
        7,
        "ROUTING_OPTIMAL",
        0.01,
        exact.fixed_vehicle_cost,
        exact_solution,
        verify_public_vrptw_solution(instance, exact_solution),
    )

    same = compare_candidate(instance, exact_candidate, exact, 1000)
    assert same["status"] == "COMPARABLE_SAME_VEHICLE_COUNT"
    assert same["transformed_distance_gap_percent"] == 0

    singleton_columns = tuple(
        column for column in enumeration.columns if len(column.customer_ids) == 1
    )
    split_solution = exact_cross_check._solution_from_columns(instance, singleton_columns)
    split_candidate = replace(
        exact_candidate,
        solution=split_solution,
        verification=verify_public_vrptw_solution(instance, split_solution),
    )
    different = compare_candidate(instance, split_candidate, exact, 1000)
    assert different == {
        "status": "VEHICLE_COUNT_DIFFERENCE",
        "vehicle_count_gap": 1,
        "transformed_distance_gap_percent": None,
    }

    unavailable = compare_candidate(
        instance,
        replace(exact_candidate, solution=None, verification=None),
        replace(exact, ground_truth_status="OPTIMALITY_NOT_PROVEN"),
        1000,
    )
    assert unavailable["status"] == "GAP_NOT_APPLICABLE"


def test_execute_cross_check_records_proof_scope_lineage_and_limits() -> None:
    selection = ExactSelection("T", "TINY101", "TINY101-PREFIX-02", "2" * 64)
    protocol = protocol_for(selection)
    source_protocol = load_solomon_protocol(SOURCE_PROTOCOL)

    payload = execute_cross_check(
        protocol,
        source_protocol,
        parsed(tiny_instance()),
        selection,
        campaign_id="campaign-test",
        code_revision="a" * 40,
    )

    instance_payload = payload["instance"]
    enumeration_payload = payload["enumeration"]
    exact_payload = payload["exact_reference"]
    claim_payload = payload["claim_scope"]
    comparison_payload = payload["comparison"]
    assert isinstance(instance_payload, dict)
    assert isinstance(enumeration_payload, dict)
    assert isinstance(exact_payload, dict)
    assert isinstance(claim_payload, dict)
    assert isinstance(comparison_payload, dict)
    assert instance_payload["customer_ids"] == [1, 2]
    assert enumeration_payload["complete"] is True
    assert exact_payload["status"] == "OPTIMAL"
    assert exact_payload["ground_truth_status"] == "TRANSFORMED_MODEL_GROUND_TRUTH"
    assert claim_payload["source_double_optimality_proven"] is False
    assert comparison_payload["status"] == "COMPARABLE_SAME_VEHICLE_COUNT"

    with pytest.raises(ExactCrossCheckError, match="code revision"):
        execute_cross_check(
            protocol,
            source_protocol,
            parsed(tiny_instance()),
            selection,
            campaign_id="campaign-test",
            code_revision="short",
        )


def test_run_writes_immutable_artifact_without_executing_public_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    protocol = load_exact_protocol(PROTOCOL)
    selected = protocol.selection("C101")
    fixture = parsed(
        tiny_instance(instance_id="C101", capacity=1, customer_count=8),
        selected.source_sha256,
    )
    monkeypatch.setattr(exact_cross_check, "load_public_benchmark", lambda *_: fixture)
    output = tmp_path / "experiments" / "r3" / "R3-315" / "campaign"

    path = run_selected_instance(
        PROTOCOL,
        SOURCE_PROTOCOL,
        tmp_path,
        output,
        "C101",
        "campaign",
        "b" * 40,
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["instance"]["customer_count"] == 8
    assert payload["exact_reference"]["ground_truth_status"] == ("TRANSFORMED_MODEL_GROUND_TRUTH")
    assert path.with_suffix(".json.sha256").is_file()
    with pytest.raises(ExactCrossCheckError, match="already exists"):
        run_selected_instance(
            PROTOCOL,
            SOURCE_PROTOCOL,
            tmp_path,
            output,
            "C101",
            "campaign",
            "b" * 40,
        )


def test_campaign_summary_checks_identity_hashes_and_retains_all_six(tmp_path: Path) -> None:
    protocol = load_exact_protocol(PROTOCOL)
    output = tmp_path / "experiments" / "r3" / "R3-315" / "campaign"
    output.mkdir(parents=True)
    for selection in protocol.selections:
        exact_cross_check._write_json_once(
            output / f"{selection.source_instance_id.lower()}.json",
            {
                "campaign_id": "campaign",
                "code_revision": "c" * 40,
                "exact_reference": {"ground_truth_status": "TRANSFORMED_MODEL_GROUND_TRUTH"},
                "comparison": {"status": "COMPARABLE_SAME_VEHICLE_COUNT"},
            },
        )

    summary = summarize_campaign(PROTOCOL, tmp_path, output, "campaign", "c" * 40)
    payload = json.loads(summary.read_text(encoding="utf-8"))
    assert payload["selected_count"] == payload["retained_count"] == 6
    assert payload["transformed_ground_truth_count"] == 6
    assert payload["comparable_same_vehicle_count"] == 6
    assert payload["claim_disposition"] == "C-NO-CLAIM"

    first = output / "c101.json"
    first.write_text("{}", encoding="utf-8")
    with pytest.raises(ExactCrossCheckError, match="checksum mismatch"):
        summarize_campaign(PROTOCOL, tmp_path, output, "campaign", "c" * 40)


def test_output_boundary_source_hash_and_cli_fail_closed(tmp_path: Path) -> None:
    protocol = load_exact_protocol(PROTOCOL)
    source_copy = tmp_path / "source.json"
    source_copy.write_text("{}", encoding="utf-8")

    with pytest.raises(ExactCrossCheckError, match="source protocol checksum"):
        run_selected_instance(
            PROTOCOL,
            source_copy,
            tmp_path,
            tmp_path / "experiments" / "r3" / "R3-315" / "campaign",
            "C101",
            "campaign",
            "d" * 40,
        )
    with pytest.raises(ExactCrossCheckError, match="below the frozen data root"):
        exact_cross_check._validated_output_directory(protocol, tmp_path, ROOT)
    assert (
        main(
            [
                "summary",
                "--protocol",
                str(tmp_path / "missing"),
                "--data-root",
                str(tmp_path),
                "--output",
                str(tmp_path / "output"),
                "--campaign-id",
                "campaign",
                "--code-revision",
                "e" * 40,
            ]
        )
        == 2
    )


def test_cli_dispatches_run_and_summary_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "result.json"
    monkeypatch.setattr(exact_cross_check, "run_selected_instance", lambda *_: output)
    common = [
        "--protocol",
        str(PROTOCOL),
        "--data-root",
        str(tmp_path),
        "--output",
        str(tmp_path / "output"),
        "--campaign-id",
        "campaign",
        "--code-revision",
        "f" * 40,
    ]
    assert (
        main(
            [
                "run",
                *common,
                "--source-protocol",
                str(SOURCE_PROTOCOL),
                "--instance",
                "C101",
            ]
        )
        == 0
    )
    assert str(output) in capsys.readouterr().out

    monkeypatch.setattr(exact_cross_check, "summarize_campaign", lambda *_: output)
    assert main(["summary", *common]) == 0
    assert str(output) in capsys.readouterr().out
