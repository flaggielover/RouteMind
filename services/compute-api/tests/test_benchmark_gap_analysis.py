from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

from routemind_compute.application import benchmark_gap_analysis
from routemind_compute.application.benchmark_gap_analysis import (
    BenchmarkGapAnalysisError,
    FrozenGapInput,
    GapAnalysisProtocol,
    analyze_frozen_results,
    load_gap_analysis_protocol,
    main,
    run_gap_analysis,
)

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = (
    ROOT / "docs" / "research" / "r3" / "manifests" / "gap-analysis" / "bks-gap-analysis-v1.json"
)
REVISION = "a" * 40


def _write_json(path: Path, payload: object, *, sidecar: bool = False) -> tuple[int, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    path.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    if sidecar:
        path.with_suffix(path.suffix + ".sha256").write_text(digest + "\n", encoding="ascii")
    return len(raw), digest


def _solomon_run(index: int) -> dict[str, object]:
    if index >= 4:
        return {
            "instance_id": f"S{index}",
            "outcome": "TIMEOUT_NO_FEASIBLE",
            "accepted_verified_complete": False,
            "vehicles": None,
            "distance_2dp": None,
            "reference_vehicles": 10,
            "reference_distance": 100.0,
            "reference_comparison": "REFERENCE_GAP_NOT_APPLICABLE",
            "distance_gap_percent": None,
        }
    vehicles = (10, 10, 11, 9)[index]
    distance = (100.0, 110.0, 120.0, 90.0)[index]
    comparison = (
        "COMPARABLE_SAME_VEHICLE_COUNT",
        "COMPARABLE_SAME_VEHICLE_COUNT",
        "VEHICLE_COUNT_WORSE",
        "VEHICLE_COUNT_BETTER",
    )[index]
    return {
        "instance_id": f"S{index}",
        "outcome": "TIMEOUT_WITH_FEASIBLE",
        "accepted_verified_complete": True,
        "vehicles": vehicles,
        "distance_2dp": distance,
        "reference_vehicles": 10,
        "reference_distance": 100.0,
        "reference_comparison": comparison,
        "distance_gap_percent": (distance - 100.0) if vehicles == 10 else None,
    }


def _homberger_run(index: int) -> dict[str, object]:
    if index == 29:
        return {
            "instance_id": "H29",
            "customers": 1000,
            "outcome": "TIMEOUT_NO_FEASIBLE",
            "vehicles": None,
            "distance_2dp": None,
            "reference_vehicles": 10,
            "reference_distance": 100.0,
            "comparison": "REFERENCE_GAP_NOT_APPLICABLE",
        }
    outcome = "FEASIBLE_INCUMBENT" if index == 0 else "TIMEOUT_WITH_FEASIBLE"
    if index < 20:
        vehicles = 11 + index % 3
        comparison = "VEHICLE_COUNT_WORSE"
        distance_gap: float | None = None
    elif index < 24:
        vehicles = 10
        comparison = "COMPARABLE_SAME_VEHICLE_COUNT"
        distance_gap = float(index - 19)
    else:
        vehicles = 20
        comparison = "REFERENCE_QUALITY_REVIEW"
        distance_gap = None
    run: dict[str, object] = {
        "instance_id": f"H{index}",
        "customers": 200 + 200 * (index // 6),
        "outcome": outcome,
        "vehicles": vehicles,
        "distance_2dp": 100.0 + (distance_gap or 20.0),
        "reference_vehicles": 10,
        "reference_distance": 100.0,
        "comparison": comparison,
    }
    if comparison == "COMPARABLE_SAME_VEHICLE_COUNT":
        run["distance_gap_percent"] = distance_gap
    return run


def _exact_artifact() -> dict[str, object]:
    verification = {"valid": True, "complete": True}
    return {
        "campaign_id": "exact-campaign",
        "code_revision": REVISION,
        "comparison": {
            "status": "COMPARABLE_SAME_VEHICLE_COUNT",
            "vehicle_count_gap": 0,
            "candidate_transformed_distance": 100,
            "exact_transformed_distance": 100,
            "transformed_distance_gap_percent": 0.0,
        },
        "candidate": {
            "solution": {"claimed_vehicle_count": 1},
            "verification": verification,
        },
        "exact_reference": {
            "status": "OPTIMAL",
            "ground_truth_status": "TRANSFORMED_MODEL_GROUND_TRUTH",
            "objective_value": 1000,
            "best_objective_bound": 1000,
            "selected_route_count": 1,
            "verification": verification,
        },
    }


def _build_fixture(tmp_path: Path) -> tuple[GapAnalysisProtocol, Path, Path, dict[str, Path]]:
    repository = tmp_path / "repository"
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True)
    paths = {
        "R3-311": repository / "inputs" / "solomon.json",
        "R3-312": repository / "inputs" / "homberger.json",
        "R3-315": repository / "inputs" / "exact.json",
    }
    solomon = {
        "schema_version": "routemind-solomon-committed-summary-v1",
        "task_id": "R3-311",
        "manifest_id": "r3-311-solomon-stratified-six-v1",
        "selection": {"selected": 6, "retained": 6},
        "outcomes": {"TIMEOUT_WITH_FEASIBLE": 4, "TIMEOUT_NO_FEASIBLE": 2},
        "runs": [_solomon_run(index) for index in range(6)],
    }
    homberger = {
        "schema_version": "routemind-homberger-committed-summary-v1",
        "task_id": "R3-312",
        "manifest_id": "r3-312-gh-scale-first-replicates-v1",
        "selection": {"selected": 30, "retained": 30},
        "result": {
            "outcomes": {
                "FEASIBLE_INCUMBENT": 1,
                "TIMEOUT_WITH_FEASIBLE": 28,
                "TIMEOUT_NO_FEASIBLE": 1,
            }
        },
        "runs": [_homberger_run(index) for index in range(30)],
    }
    _, solomon_sha = _write_json(paths["R3-311"], solomon)
    _, homberger_sha = _write_json(paths["R3-312"], homberger)

    external_relative = "experiments/r3/R3-315/exact-campaign"
    external = data_root.joinpath(*external_relative.split("/"))
    exact_runs: list[dict[str, object]] = []
    for index in range(6):
        artifact_name = f"e{index}.json"
        size, digest = _write_json(external / artifact_name, _exact_artifact(), sidecar=True)
        exact_runs.append(
            {
                "instance_id": f"S{index}",
                "derived_instance_id": f"S{index}-PREFIX-08",
                "candidate_status": "ROUTING_SUCCESS",
                "exact_status": "OPTIMAL",
                "vehicles": 1,
                "transformed_distance": 100,
                "transformed_distance_gap_percent": 0.0,
                "artifact": {"name": artifact_name, "bytes": size, "sha256": digest},
            }
        )
    exact = {
        "schema_version": "routemind-exact-cross-check-committed-summary-v1",
        "task_id": "R3-315",
        "manifest_id": "r3-315-solomon-prefix-eight-exact-v1",
        "campaign_id": "exact-campaign",
        "code_revision": REVISION,
        "external_result_relative_root": external_relative,
        "selection": {"selected": 6, "retained": 6},
        "result": {
            "enumeration_complete": 6,
            "cp_sat_optimal": 6,
            "objective_equals_best_bound": 6,
            "independently_verified": 6,
            "transformed_model_ground_truth": 6,
            "candidate_same_vehicle_count": 6,
            "candidate_zero_transformed_distance_gap": 6,
        },
        "runs": exact_runs,
    }
    _, exact_sha = _write_json(paths["R3-315"], exact)
    inputs = (
        FrozenGapInput(
            "R3-311",
            "inputs/solomon.json",
            solomon_sha,
            "routemind-solomon-committed-summary-v1",
            "r3-311-solomon-stratified-six-v1",
            6,
            6,
            "SOURCE_DOUBLE_BKS",
        ),
        FrozenGapInput(
            "R3-312",
            "inputs/homberger.json",
            homberger_sha,
            "routemind-homberger-committed-summary-v1",
            "r3-312-gh-scale-first-replicates-v1",
            30,
            30,
            "SOURCE_DOUBLE_BKS",
        ),
        FrozenGapInput(
            "R3-315",
            "inputs/exact.json",
            exact_sha,
            "routemind-exact-cross-check-committed-summary-v1",
            "r3-315-solomon-prefix-eight-exact-v1",
            6,
            6,
            "DERIVED_CONSERVATIVE_INTEGER_OPTIMUM",
        ),
    )
    return (
        GapAnalysisProtocol(
            "test-manifest", "f" * 64, REVISION, inputs, 36, 6, 42, "experiments/r3/R3-316"
        ),
        repository,
        data_root,
        paths,
    )


def _refresh_input(protocol: GapAnalysisProtocol, task_id: str, path: Path) -> GapAnalysisProtocol:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    inputs = tuple(
        replace(item, sha256=digest) if item.task_id == task_id else item
        for item in protocol.inputs
    )
    return replace(protocol, inputs=inputs)


def _load_payload(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return cast(dict[str, Any], value)


def _rewrite(path: Path, payload: object) -> None:
    _write_json(path, payload)


def _set_path(payload: Any, path: tuple[object, ...], value: object) -> None:
    current = payload
    for item in path[:-1]:
        current = current[item]
    current[path[-1]] = value


def test_frozen_protocol_loads_all_inputs_domains_and_digest() -> None:
    protocol = load_gap_analysis_protocol(PROTOCOL)

    assert protocol.manifest_id == "r3-316-bks-gap-analysis-v1"
    assert protocol.manifest_sha256 == hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    assert tuple(item.task_id for item in protocol.inputs) == ("R3-311", "R3-312", "R3-315")
    assert (protocol.source_expected_records, protocol.exact_expected_records) == (36, 6)
    assert protocol.ledger_expected_records == 42
    assert protocol.input_for("R3-312").selected == 30
    with pytest.raises(BenchmarkGapAnalysisError, match="not uniquely frozen"):
        protocol.input_for("R3-999")


@pytest.mark.parametrize(
    ("path", "value", "message"),
    (
        (("schema_version",), "other", "schema is unsupported"),
        (("task_id",), "R3-X", "must be R3-316"),
        (("material_execution_started",), True, "precede material"),
        (("material_execution_started",), "false", "must be boolean"),
        (("frozen_against_revision",), "short", "frozen revision"),
        (("inputs", 0, "task_id"), "R3-312", "preserve"),
        (("inputs", 0, "path"), "../outside", "safe relative"),
        (("inputs", 0, "sha256"), "short", "lowercase SHA-256"),
        (("inputs", 0, "selected"), 5, "6/30/6"),
        (("inputs", 0, "retained"), 5, "retain every"),
        (("inputs", 0, "analysis_domain"), "OTHER", "domains are invalid"),
        (("analysis_universes", "source_double_bks", "task_ids"), ["R3-311"], "source analysis"),
        (
            ("analysis_universes", "derived_conservative_integer_optimum", "task_ids"),
            ["R3-314"],
            "exact analysis universe",
        ),
        (
            ("analysis_universes", "all_outcome_ledger", "task_ids"),
            ["R3-311"],
            "all-outcome ledger",
        ),
        (("analysis_universes", "source_double_bks", "expected_records"), 35, "36/6/42"),
        (("analysis_universes", "source_double_bks", "expected_records"), 0, "must be positive"),
        (("objective_semantics", "source"), "DISTANCE", "remain hierarchical"),
        (("objective_semantics", "direction"), "positive is better", "direction differs"),
        (
            ("reference_eligibility", "REFERENCE_QUALITY_REVIEW", "vehicle_gap_allowed"),
            True,
            "eligibility drifted",
        ),
        (
            ("reference_eligibility", "VEHICLE_COUNT_WORSE", "distance_gap_allowed"),
            True,
            "distance eligibility drifted",
        ),
        (("descriptive_statistics", "fields"), ["n"], "fields differ"),
        (("descriptive_statistics", "percentile_method"), "nearest", "Type 7"),
        (("outcome_accounting", "r3_317_outcomes"), ["FAILED"], "accounting is incomplete"),
        (("artifact_policy", "external_result_relative_root"), "other", "result root differs"),
        (("execution_policy", "threads"), 2, "one-thread"),
        (("execution_policy", "threads"), "1", "must be an integer"),
    ),
)
def test_protocol_rejects_frozen_contract_drift(
    tmp_path: Path, path: tuple[object, ...], value: object, message: str
) -> None:
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    _set_path(payload, path, value)
    mutated = tmp_path / "manifest.json"
    _rewrite(mutated, payload)

    with pytest.raises(BenchmarkGapAnalysisError, match=message):
        load_gap_analysis_protocol(mutated)


def test_protocol_rejects_unreadable_missing_and_non_object_fields(tmp_path: Path) -> None:
    with pytest.raises(BenchmarkGapAnalysisError, match="protocol is unreadable"):
        load_gap_analysis_protocol(tmp_path / "missing.json")

    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    del payload["schema_version"]
    path = tmp_path / "manifest.json"
    _rewrite(path, payload)
    with pytest.raises(BenchmarkGapAnalysisError, match="schema_version is required"):
        load_gap_analysis_protocol(path)

    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    payload["inputs"] = "not-an-array"
    _rewrite(path, payload)
    with pytest.raises(BenchmarkGapAnalysisError, match="inputs must be an array"):
        load_gap_analysis_protocol(path)

    payload["inputs"] = [1]
    _rewrite(path, payload)
    with pytest.raises(BenchmarkGapAnalysisError, match="frozen input must be an object"):
        load_gap_analysis_protocol(path)


def test_analysis_accounts_all_records_and_keeps_domains_separate(tmp_path: Path) -> None:
    protocol, repository, data_root, _ = _build_fixture(tmp_path)
    payload = analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 123)

    assert payload["audit"] == {
        "input_files": 3,
        "upstream_records": 42,
        "accounted_records": 42,
        "excluded_records": 0,
        "source_double_bks_records": 36,
        "derived_exact_records": 6,
        "verified_external_exact_artifacts": 6,
        "duplicate_record_ids": 0,
        "errors": 0,
    }
    source = payload["source_double_bks"]
    assert isinstance(source, dict)
    combined = source["combined"]
    assert isinstance(combined, dict)
    assert combined["records"] == 36
    rates = combined["rates"]
    assert isinstance(rates, dict)
    assert rates["any_timeout_rate"] == pytest.approx(35 / 36)
    by_task = source["by_task"]
    assert isinstance(by_task, dict)
    solomon = by_task["R3-311"]
    assert isinstance(solomon, dict)
    vehicle = solomon["vehicle_gap_percent"]
    assert isinstance(vehicle, dict)
    assert vehicle["n"] == 4
    assert vehicle["minimum"] == -10.0
    assert vehicle["median"] == 0.0
    assert vehicle["p90"] == pytest.approx(7.0)
    assert vehicle["maximum"] == 10.0
    distance = combined["same_vehicle_distance_gap_percent"]
    assert isinstance(distance, dict)
    assert distance["n"] == 6
    assert distance["median"] == 2.5
    assert distance["p90"] == 7.0
    exact = payload["derived_conservative_integer_optimum"]
    assert isinstance(exact, dict)
    assert exact["transformed_exact_gap_percent"] == {
        "n": 6,
        "minimum": 0.0,
        "median": 0.0,
        "p90": 0.0,
        "maximum": 0.0,
    }
    ledger = payload["all_outcome_ledger"]
    assert isinstance(ledger, list)
    assert len(ledger) == 42
    assert payload["statistical_disposition"] == "S-PASS"
    assert payload["claim_disposition"] == "C-NO-CLAIM"


@pytest.mark.parametrize(
    ("campaign", "revision", "ci", "message"),
    (
        ("", REVISION, 1, "campaign id"),
        ("x", "short", 1, "code revision"),
        ("x", REVISION, 0, "CI run"),
    ),
)
def test_analysis_rejects_invalid_execution_identity(
    tmp_path: Path, campaign: str, revision: str, ci: int, message: str
) -> None:
    protocol, repository, data_root, _ = _build_fixture(tmp_path)
    with pytest.raises(BenchmarkGapAnalysisError, match=message):
        analyze_frozen_results(protocol, repository, data_root, campaign, revision, ci)


@pytest.mark.parametrize(
    ("source_count", "exact_count", "ledger_count", "message"),
    (
        (35, 6, 42, "source record count"),
        (36, 5, 42, "exact record count"),
        (36, 6, 41, "all-outcome ledger"),
    ),
)
def test_analysis_rejects_runtime_universe_count_drift(
    tmp_path: Path, source_count: int, exact_count: int, ledger_count: int, message: str
) -> None:
    protocol, repository, data_root, _ = _build_fixture(tmp_path)
    protocol = replace(
        protocol,
        source_expected_records=source_count,
        exact_expected_records=exact_count,
        ledger_expected_records=ledger_count,
    )
    with pytest.raises(BenchmarkGapAnalysisError, match=message):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)


def test_analysis_rejects_frozen_input_checksum_schema_and_task_drift(tmp_path: Path) -> None:
    protocol, repository, data_root, paths = _build_fixture(tmp_path)
    paths["R3-311"].write_text("{}", encoding="utf-8")
    with pytest.raises(BenchmarkGapAnalysisError, match="checksum mismatch"):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)

    protocol, repository, data_root, paths = _build_fixture(tmp_path / "schema")
    payload = _load_payload(paths["R3-312"])
    payload["schema_version"] = "other"
    _rewrite(paths["R3-312"], payload)
    protocol = _refresh_input(protocol, "R3-312", paths["R3-312"])
    with pytest.raises(BenchmarkGapAnalysisError, match="schema drifted"):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)

    payload["schema_version"] = "routemind-homberger-committed-summary-v1"
    payload["task_id"] = "R3-X"
    _rewrite(paths["R3-312"], payload)
    protocol = _refresh_input(protocol, "R3-312", paths["R3-312"])
    with pytest.raises(BenchmarkGapAnalysisError, match="task identity drifted"):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)

    payload["task_id"] = "R3-312"
    payload["manifest_id"] = "other"
    _rewrite(paths["R3-312"], payload)
    protocol = _refresh_input(protocol, "R3-312", paths["R3-312"])
    with pytest.raises(BenchmarkGapAnalysisError, match="manifest drifted"):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)

    paths["R3-312"].write_text("not-json", encoding="utf-8")
    protocol = _refresh_input(protocol, "R3-312", paths["R3-312"])
    with pytest.raises(BenchmarkGapAnalysisError, match="summary is unreadable"):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)


def test_source_analysis_rejects_counts_duplicates_and_outcome_drift(tmp_path: Path) -> None:
    protocol, repository, data_root, paths = _build_fixture(tmp_path)
    payload = _load_payload(paths["R3-311"])
    payload["selection"]["selected"] = 5
    _rewrite(paths["R3-311"], payload)
    protocol = _refresh_input(protocol, "R3-311", paths["R3-311"])
    with pytest.raises(BenchmarkGapAnalysisError, match="selection counts drifted"):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)

    protocol, repository, data_root, paths = _build_fixture(tmp_path / "duplicate")
    payload = _load_payload(paths["R3-311"])
    payload["runs"][1]["instance_id"] = payload["runs"][0]["instance_id"]
    _rewrite(paths["R3-311"], payload)
    protocol = _refresh_input(protocol, "R3-311", paths["R3-311"])
    with pytest.raises(BenchmarkGapAnalysisError, match="identities are not unique"):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)

    protocol, repository, data_root, paths = _build_fixture(tmp_path / "outcomes")
    payload = _load_payload(paths["R3-312"])
    payload["result"]["outcomes"]["TIMEOUT_WITH_FEASIBLE"] = 27
    _rewrite(paths["R3-312"], payload)
    protocol = _refresh_input(protocol, "R3-312", paths["R3-312"])
    with pytest.raises(BenchmarkGapAnalysisError, match="outcome counts drifted"):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)

    protocol, repository, data_root, paths = _build_fixture(tmp_path / "run-count")
    payload = _load_payload(paths["R3-311"])
    payload["runs"].pop()
    _rewrite(paths["R3-311"], payload)
    protocol = _refresh_input(protocol, "R3-311", paths["R3-311"])
    with pytest.raises(BenchmarkGapAnalysisError, match="run count drifted"):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)

    protocol, repository, data_root, paths = _build_fixture(tmp_path / "reported-outcome")
    payload = _load_payload(paths["R3-311"])
    payload["outcomes"] = {"OTHER": 6}
    _rewrite(paths["R3-311"], payload)
    protocol = _refresh_input(protocol, "R3-311", paths["R3-311"])
    with pytest.raises(BenchmarkGapAnalysisError, match="unknown reported outcome"):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ({"outcome": "OTHER"}, "unknown outcome"),
        ({"accepted_verified_complete": False}, "incumbent/outcome mismatch"),
        ({"vehicles": None}, "incumbent fields are invalid"),
        ({"reference_comparison": "OTHER"}, "reference status is unknown"),
        (
            {"reference_comparison": "COMPARABLE_SAME_VEHICLE_COUNT", "vehicles": 11},
            "equal-vehicle",
        ),
        ({"reference_comparison": "VEHICLE_COUNT_WORSE", "vehicles": 9}, "worse-vehicle"),
        ({"reference_comparison": "VEHICLE_COUNT_BETTER", "vehicles": 11}, "better-vehicle"),
        ({"distance_gap_percent": 99.0}, "distance gap mismatch"),
        ({"reference_distance": 0.0}, "reference distance is invalid"),
        ({"reference_distance": "bad"}, "must be finite numeric"),
        ({"vehicles": "bad"}, "integer or null"),
        ({"distance_gap_percent": "bad"}, "finite numeric or null"),
    ),
)
def test_source_analysis_rejects_semantic_mutations(
    tmp_path: Path, mutation: dict[str, object], message: str
) -> None:
    protocol, repository, data_root, paths = _build_fixture(tmp_path)
    payload = _load_payload(paths["R3-311"])
    payload["runs"][0].update(mutation)
    if "outcome" in mutation:
        payload["outcomes"] = {"OTHER": 1, "TIMEOUT_WITH_FEASIBLE": 3, "TIMEOUT_NO_FEASIBLE": 2}
    _rewrite(paths["R3-311"], payload)
    protocol = _refresh_input(protocol, "R3-311", paths["R3-311"])
    with pytest.raises(BenchmarkGapAnalysisError, match=message):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)


def test_source_analysis_rejects_forbidden_gap_and_no_incumbent_fields(tmp_path: Path) -> None:
    protocol, repository, data_root, paths = _build_fixture(tmp_path)
    payload = _load_payload(paths["R3-311"])
    payload["runs"][2]["distance_gap_percent"] = 1.0
    _rewrite(paths["R3-311"], payload)
    protocol = _refresh_input(protocol, "R3-311", paths["R3-311"])
    with pytest.raises(BenchmarkGapAnalysisError, match="forbidden distance gap"):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)

    protocol, repository, data_root, paths = _build_fixture(tmp_path / "null")
    payload = _load_payload(paths["R3-311"])
    payload["runs"][4]["vehicles"] = 1
    _rewrite(paths["R3-311"], payload)
    protocol = _refresh_input(protocol, "R3-311", paths["R3-311"])
    with pytest.raises(BenchmarkGapAnalysisError, match="no-incumbent fields"):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)

    protocol, repository, data_root, paths = _build_fixture(tmp_path / "na-incumbent")
    payload = _load_payload(paths["R3-311"])
    payload["runs"][0]["reference_comparison"] = "REFERENCE_GAP_NOT_APPLICABLE"
    payload["runs"][0]["distance_gap_percent"] = None
    _rewrite(paths["R3-311"], payload)
    protocol = _refresh_input(protocol, "R3-311", paths["R3-311"])
    with pytest.raises(BenchmarkGapAnalysisError, match="N/A comparison has an incumbent"):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)

    protocol, repository, data_root, paths = _build_fixture(tmp_path / "review-no-incumbent")
    payload = _load_payload(paths["R3-311"])
    payload["runs"][4]["reference_comparison"] = "REFERENCE_QUALITY_REVIEW"
    _rewrite(paths["R3-311"], payload)
    protocol = _refresh_input(protocol, "R3-311", paths["R3-311"])
    with pytest.raises(BenchmarkGapAnalysisError, match="quality review lacks an incumbent"):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)


def test_exact_analysis_rejects_aggregate_and_artifact_checksum_drift(tmp_path: Path) -> None:
    protocol, repository, data_root, paths = _build_fixture(tmp_path)
    payload = _load_payload(paths["R3-315"])
    payload["result"]["cp_sat_optimal"] = 5
    _rewrite(paths["R3-315"], payload)
    protocol = _refresh_input(protocol, "R3-315", paths["R3-315"])
    with pytest.raises(BenchmarkGapAnalysisError, match="aggregate cp_sat_optimal"):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)

    protocol, repository, data_root, paths = _build_fixture(tmp_path / "checksum")
    payload = _load_payload(paths["R3-315"])
    artifact = payload["runs"][0]["artifact"]
    artifact_path = data_root / payload["external_result_relative_root"] / artifact["name"]
    artifact_path.with_suffix(".json.sha256").write_text("0" * 64 + "\n", encoding="ascii")
    with pytest.raises(BenchmarkGapAnalysisError, match="checksum mismatch"):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)


def test_exact_analysis_rejects_summary_identity_and_artifact_lineage_drift(
    tmp_path: Path,
) -> None:
    protocol, repository, data_root, paths = _build_fixture(tmp_path)
    payload = _load_payload(paths["R3-315"])
    payload["selection"]["retained"] = 5
    _rewrite(paths["R3-315"], payload)
    protocol = _refresh_input(protocol, "R3-315", paths["R3-315"])
    with pytest.raises(BenchmarkGapAnalysisError, match="selection counts drifted"):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)

    protocol, repository, data_root, paths = _build_fixture(tmp_path / "run-count")
    payload = _load_payload(paths["R3-315"])
    payload["runs"].pop()
    _rewrite(paths["R3-315"], payload)
    protocol = _refresh_input(protocol, "R3-315", paths["R3-315"])
    with pytest.raises(BenchmarkGapAnalysisError, match="run count drifted"):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)

    protocol, repository, data_root, paths = _build_fixture(tmp_path / "duplicate")
    payload = _load_payload(paths["R3-315"])
    payload["runs"][1]["derived_instance_id"] = payload["runs"][0]["derived_instance_id"]
    _rewrite(paths["R3-315"], payload)
    protocol = _refresh_input(protocol, "R3-315", paths["R3-315"])
    with pytest.raises(BenchmarkGapAnalysisError, match="derived identities are not unique"):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)

    protocol, repository, data_root, paths = _build_fixture(tmp_path / "status")
    payload = _load_payload(paths["R3-315"])
    payload["runs"][0]["exact_status"] = "FEASIBLE"
    _rewrite(paths["R3-315"], payload)
    protocol = _refresh_input(protocol, "R3-315", paths["R3-315"])
    with pytest.raises(BenchmarkGapAnalysisError, match="lacks exact optimal"):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)

    protocol, repository, data_root, paths = _build_fixture(tmp_path / "missing-artifact")
    payload = _load_payload(paths["R3-315"])
    first = payload["runs"][0]["artifact"]
    artifact_path = data_root / payload["external_result_relative_root"] / first["name"]
    artifact_path.unlink()
    with pytest.raises(BenchmarkGapAnalysisError, match="artifact is unreadable"):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)

    protocol, repository, data_root, paths = _build_fixture(tmp_path / "bytes")
    payload = _load_payload(paths["R3-315"])
    payload["runs"][0]["artifact"]["bytes"] += 1
    _rewrite(paths["R3-315"], payload)
    protocol = _refresh_input(protocol, "R3-315", paths["R3-315"])
    with pytest.raises(BenchmarkGapAnalysisError, match="byte count mismatch"):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)

    protocol, repository, data_root, paths = _build_fixture(tmp_path / "lineage")
    payload = _load_payload(paths["R3-315"])
    first = payload["runs"][0]["artifact"]
    artifact_path = data_root / payload["external_result_relative_root"] / first["name"]
    artifact = _load_payload(artifact_path)
    artifact["campaign_id"] = "other"
    size, digest = _write_json(artifact_path, artifact, sidecar=True)
    first.update({"bytes": size, "sha256": digest})
    _rewrite(paths["R3-315"], payload)
    protocol = _refresh_input(protocol, "R3-315", paths["R3-315"])
    with pytest.raises(BenchmarkGapAnalysisError, match="lineage mismatch"):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)


@pytest.mark.parametrize(
    ("path", "value", "message"),
    (
        (("comparison", "status"), "OTHER", "not hierarchical"),
        (("comparison", "vehicle_count_gap"), 1, "vehicle counts differ"),
        (("comparison", "candidate_transformed_distance"), 110, "transformed gap mismatch"),
        (("exact_reference", "status"), "FEASIBLE", "proof scope drifted"),
        (("exact_reference", "best_objective_bound"), 999, "exact bound differs"),
        (("candidate", "solution", "claimed_vehicle_count"), 2, "vehicle lineage drifted"),
        (("candidate", "verification", "valid"), False, "candidate verification failed"),
    ),
)
def test_exact_analysis_rejects_artifact_semantic_drift(
    tmp_path: Path, path: tuple[object, ...], value: object, message: str
) -> None:
    protocol, repository, data_root, paths = _build_fixture(tmp_path)
    summary = _load_payload(paths["R3-315"])
    run = summary["runs"][0]
    artifact_path = data_root / summary["external_result_relative_root"] / run["artifact"]["name"]
    artifact = _load_payload(artifact_path)
    _set_path(artifact, path, value)
    size, digest = _write_json(artifact_path, artifact, sidecar=True)
    run["artifact"] = {"name": run["artifact"]["name"], "bytes": size, "sha256": digest}
    _rewrite(paths["R3-315"], summary)
    protocol = _refresh_input(protocol, "R3-315", paths["R3-315"])
    with pytest.raises(BenchmarkGapAnalysisError, match=message):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)


def test_exact_analysis_rejects_summary_transformed_distance_drift(tmp_path: Path) -> None:
    protocol, repository, data_root, paths = _build_fixture(tmp_path)
    payload = _load_payload(paths["R3-315"])
    payload["runs"][0]["transformed_distance"] = 99
    _rewrite(paths["R3-315"], payload)
    protocol = _refresh_input(protocol, "R3-315", paths["R3-315"])
    with pytest.raises(BenchmarkGapAnalysisError, match="transformed distance drifted"):
        analyze_frozen_results(protocol, repository, data_root, "campaign", REVISION, 1)


def test_empty_and_invalid_descriptions_and_root_escape(tmp_path: Path) -> None:
    assert benchmark_gap_analysis._describe(()) == {
        "n": 0,
        "minimum": None,
        "median": None,
        "p90": None,
        "maximum": None,
    }
    with pytest.raises(BenchmarkGapAnalysisError, match="non-finite"):
        benchmark_gap_analysis._describe((float("nan"),))
    with pytest.raises(BenchmarkGapAnalysisError, match="escapes its root"):
        benchmark_gap_analysis._resolve_below(tmp_path, "../outside", "fixture")


def test_run_writes_immutable_result_and_cli_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    protocol, repository, data_root, _ = _build_fixture(tmp_path)
    manifest = tmp_path / "manifest.json"
    monkeypatch.setattr(benchmark_gap_analysis, "load_gap_analysis_protocol", lambda _: protocol)
    output = data_root / "experiments" / "r3" / "R3-316" / "campaign"
    output.mkdir(parents=True)
    path = run_gap_analysis(manifest, repository, data_root, output, "campaign", REVISION, 123)

    assert path.name == "gap-analysis.json"
    assert path.with_suffix(".json.sha256").is_file()
    with pytest.raises(BenchmarkGapAnalysisError, match="already exists"):
        run_gap_analysis(manifest, repository, data_root, output, "campaign", REVISION, 123)
    with pytest.raises(BenchmarkGapAnalysisError, match="below the frozen data root"):
        run_gap_analysis(
            manifest, repository, data_root, tmp_path / "outside", "campaign", REVISION, 123
        )

    missing = data_root / "experiments" / "r3" / "R3-316" / "missing"
    with pytest.raises(BenchmarkGapAnalysisError, match="already exist"):
        run_gap_analysis(manifest, repository, data_root, missing, "campaign", REVISION, 123)
    allowed = data_root / "experiments" / "r3" / "R3-316"
    allowed.mkdir(exist_ok=True)
    with pytest.raises(BenchmarkGapAnalysisError, match="distinct campaign"):
        run_gap_analysis(manifest, repository, data_root, allowed, "campaign", REVISION, 123)
    assert (
        main(
            [
                "--protocol",
                str(tmp_path / "missing"),
                "--repository-root",
                str(repository),
                "--data-root",
                str(data_root),
                "--output-directory",
                str(output),
                "--campaign-id",
                "campaign",
                "--code-revision",
                REVISION,
                "--implementation-ci-run",
                "123",
            ]
        )
        == 2
    )
    assert "gap analysis failed" in capsys.readouterr().err

    result = tmp_path / "cli-result.json"
    monkeypatch.setattr(benchmark_gap_analysis, "run_gap_analysis", lambda *args: result)
    assert (
        main(
            [
                "--protocol",
                str(manifest),
                "--repository-root",
                str(repository),
                "--data-root",
                str(data_root),
                "--output-directory",
                str(output),
                "--campaign-id",
                "campaign",
                "--code-revision",
                REVISION,
                "--implementation-ci-run",
                "123",
            ]
        )
        == 0
    )
    assert str(result) in capsys.readouterr().out
