from __future__ import annotations

import ast
import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from routemind_compute.application import independent_reproduction as subject
from routemind_compute.application.independent_reproduction import (
    IndependentReproductionError,
    IndependentReproductionPlan,
    load_independent_reproduction_plan,
    main,
    run_independent_reproduction,
    write_independent_reproduction_result,
)

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "docs/research/r3/manifests/reproduction/r3-356-independent-reproduction-v1.json"
SOURCE = ROOT / "services/compute-api/src/routemind_compute/application/independent_reproduction.py"


def _digest(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, allow_nan=False, separators=(",", ":"), sort_keys=True
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _write(path: Path, value: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _embedded(value: dict[str, object], key: str) -> dict[str, object]:
    result = dict(value)
    result[key] = _digest(result)
    return result


def _fixture(tmp_path: Path) -> tuple[IndependentReproductionPlan, Path, Path]:
    repo = tmp_path / "repo"
    data = tmp_path / "data"

    benchmark = {
        "all_outcome_ledger": [
            {
                "analysis_domain": "SOURCE_DOUBLE_BKS",
                "record_id": "source:1",
                "outcome": "TIMEOUT_WITH_FEASIBLE",
                "reference_comparison": "COMPARABLE_SAME_VEHICLE_COUNT",
                "vehicle_gap_percent": 0.0,
                "same_vehicle_distance_gap_percent": 2.0,
            },
            {
                "analysis_domain": "DERIVED_CONSERVATIVE_INTEGER_OPTIMUM",
                "record_id": "exact:1",
                "outcome": "R3_317_NOT_APPLICABLE",
                "transformed_exact_gap_percent": 0.0,
            },
        ],
        "statistical_disposition": "S-PASS",
        "claim_disposition": "C-NO-CLAIM",
    }
    benchmark_path = data / "benchmark.json"
    benchmark_sha = _write(benchmark_path, benchmark)
    one_zero = {"n": 1, "minimum": 0.0, "median": 0.0, "p90": 0.0, "maximum": 0.0}
    one_two = {"n": 1, "minimum": 2.0, "median": 2.0, "p90": 2.0, "maximum": 2.0}
    reported = {
        "source_double_bks": {
            "vehicle_gap_percent": one_zero,
            "same_vehicle_distance_gap_percent": one_two,
        },
        "derived_conservative_integer_optimum": {
            "transformed_exact_gap_percent": one_zero,
        },
    }
    reported_path = repo / "reported.json"
    reported_sha = _write(reported_path, reported)

    pair = {
        "replicate": 0,
        "streams": [{"stream_name": name} for name in ("demand", "merchant", "courier", "traffic")],
    }
    cells = [
        {
            "regime_id": regime,
            "metric_id": metric,
            "status": status,
            "n": 1,
            "pair_seeds": [pair],
        }
        for regime in ("normal", "compute-budget")
        for metric, status in (
            ("scenario_risk_index", "PLANNED"),
            ("assignment_rate", "NON_ESTIMABLE"),
        )
    ]
    tests = [
        {
            "raw_p_value": None,
            "adjusted_p_value": None,
            "rejected": False,
        }
        for _ in range(4)
    ]
    report = {
        "cells": cells,
        "multiplicity": {"disposition": "CONFIRMATORY_NOT_EXECUTED", "tests": tests},
        "diagnostics": {
            "arm_count": 8,
            "failure_count": 0,
            "fallback_count": 0,
            "timeout_count": 0,
            "by_strategy": {"risk-aware": {}, "weighted-greedy": {}},
        },
    }
    report_digest = _digest(report)
    statistical = {"report": report, "report_digest": report_digest}
    statistical_path = data / "statistical.json"
    statistical_sha = _write(statistical_path, statistical)

    split = _embedded(
        {
            "data_availability": {"observed_record_count": 0, "status": "INSUFFICIENT_DATA"},
            "splits": {
                "calibration": {"record_count": 0},
                "held_out": {"record_count": 0},
            },
        },
        "contract_digest",
    )
    split_path = repo / "split.json"
    split_sha = _write(split_path, split)
    twin_report = _embedded(
        {"claim_policy": {"status": "C-NO-CLAIM"}},
        "plan_digest",
    )
    twin_path = repo / "twin.json"
    twin_sha = _write(twin_path, twin_report)
    rads = _embedded(
        {"analysis_plan": {"minimum_pairs_per_axis_level": 30}},
        "plan_digest",
    )
    rads_path = repo / "rads.json"
    rads_sha = _write(rads_path, rads)

    benchmark_expected = {
        "record_count": 2,
        "source_records": 1,
        "derived_records": 1,
        "source_outcomes": {"TIMEOUT_WITH_FEASIBLE": 1},
        "reference_comparisons": {"COMPARABLE_SAME_VEHICLE_COUNT": 1},
        "vehicle_gap_percent": one_zero,
        "same_vehicle_distance_gap_percent": one_two,
        "transformed_exact_gap_percent": one_zero,
        "statistical_disposition": "S-PASS",
        "claim_disposition": "C-NO-CLAIM",
    }
    statistical_expected = {
        "report_digest": report_digest,
        "regimes": ["normal", "compute-budget"],
        "metrics": ["scenario_risk_index", "assignment_rate"],
        "pairs_per_cell": 1,
        "stream_names": ["demand", "merchant", "courier", "traffic"],
        "non_estimable_assignment_regimes": ["normal", "compute-budget"],
        "multiplicity_disposition": "CONFIRMATORY_NOT_EXECUTED",
        "arm_count": 8,
        "failure_count": 0,
        "fallback_count": 0,
        "timeout_count": 0,
        "statistical_disposition": "S-FAIL",
        "claim_disposition": "C-NO-CLAIM",
    }
    twin_expected = {
        "observed_record_count": 0,
        "calibration_record_count": 0,
        "held_out_record_count": 0,
        "status": "INSUFFICIENT_DATA",
        "thresholds": "NOT_EVALUATED_NO_DATA",
        "unsupported_regimes": "NOT_ANALYZED_NO_DATA",
        "sensitivity": "NOT_RUN_NO_DATA",
        "data_limits": "INSUFFICIENT_DATA",
        "claim_status": "C-NO-CLAIM",
    }
    rads_expected = {
        "source_regime_axes": [
            "seeds",
            "demand",
            "supply",
            "merchant_delay",
            "traffic",
            "location_staleness",
            "compute_constraints",
        ],
        "unsupported_axes": ["location_noise"],
        "pairs_per_existing_regime": 1,
        "minimum_pairs_per_axis_level": 30,
        "observed_strategy_identities": ["risk-aware", "weighted-greedy"],
        "absent_variant_identities": ["RADS-H-v1", "Safe-RADS-v1"],
        "status": "INSUFFICIENT_DATA",
        "broad_claim_status": "PROHIBITED_NO_CROSS_REGIME_EVIDENCE",
        "claim_disposition": "C-NO-CLAIM",
    }
    targets: list[object] = [
        {
            "task_id": "R3-316",
            "checker": "benchmark-checker",
            "external_result_path": "benchmark.json",
            "external_result_sha256": benchmark_sha,
            "reported_result_path": "reported.json",
            "reported_result_sha256": reported_sha,
            "expected": benchmark_expected,
        },
        {
            "task_id": "R3-327",
            "checker": "statistical-checker",
            "external_result_path": "statistical.json",
            "external_result_sha256": statistical_sha,
            "expected": statistical_expected,
        },
        {
            "task_id": "R3-336",
            "checker": "twin-checker",
            "split_contract_path": "split.json",
            "split_contract_sha256": split_sha,
            "report_plan_path": "twin.json",
            "report_plan_sha256": twin_sha,
            "expected": twin_expected,
        },
        {
            "task_id": "R3-349",
            "checker": "rads-checker",
            "robustness_plan_path": "rads.json",
            "robustness_plan_sha256": rads_sha,
            "external_result_path": "statistical.json",
            "external_result_sha256": statistical_sha,
            "expected": rads_expected,
        },
    ]
    plan = IndependentReproductionPlan(
        {"reproduction_id": "fixture-reproduction", "targets": targets},
        "f" * 64,
        "e" * 64,
    )
    return plan, repo, data


def test_frozen_plan_declares_retrospective_clean_room_boundary() -> None:
    plan = load_independent_reproduction_plan(PLAN)
    assert plan.plan_digest == "aaab4e70a7daa04d6850c886edb80ac652d47f0fad89e89e75b550530f874d93"
    assert plan.manifest_sha256 == hashlib.sha256(PLAN.read_bytes()).hexdigest()
    targets = cast(list[dict[str, object]], plan.payload["targets"])
    assert tuple(target["task_id"] for target in targets) == (
        "R3-316",
        "R3-327",
        "R3-336",
        "R3-349",
    )


def test_checker_imports_only_declared_standard_library_roots() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    assert roots <= {
        "__future__",
        "argparse",
        "collections",
        "dataclasses",
        "hashlib",
        "json",
        "math",
        "os",
        "pathlib",
        "platform",
        "sys",
        "typing",
    }
    assert "routemind_compute" not in roots


def test_clean_room_checker_reproduces_all_four_targets(tmp_path: Path) -> None:
    plan, repo, data = _fixture(tmp_path)
    result = run_independent_reproduction(plan, repo, data, "a" * 40, 123)
    assert result["overall_status"] == "REPRODUCED_WITH_NO_CONTRADICTIONS"
    assert result["contradictions"] == []
    target_results = cast(list[dict[str, object]], result["target_results"])
    assert [row["status"] for row in target_results] == ["REPRODUCED"] * 4
    unsigned = {key: value for key, value in result.items() if key != "result_digest"}
    assert result["result_digest"] == _digest(unsigned)


def test_contradictions_are_retained_instead_of_raising(tmp_path: Path) -> None:
    plan, repo, data = _fixture(tmp_path)
    targets = cast(list[dict[str, object]], plan.payload["targets"])
    expected = cast(dict[str, object], targets[0]["expected"])
    expected["record_count"] = 999
    result = run_independent_reproduction(plan, repo, data, "b" * 40, 456)
    assert result["overall_status"] == "CONTRADICTIONS_RETAINED"
    contradictions = cast(list[str], result["contradictions"])
    assert any("R3-316:record_count differs" in item for item in contradictions)
    target_results = cast(list[dict[str, object]], result["target_results"])
    assert target_results[0]["status"] == "CONTRADICTED"


def test_duplicate_identity_and_embedded_digest_drift_are_retained(tmp_path: Path) -> None:
    plan, repo, data = _fixture(tmp_path)
    benchmark_path = data / "benchmark.json"
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
    benchmark["all_outcome_ledger"][1]["record_id"] = "source:1"
    targets = cast(list[dict[str, object]], plan.payload["targets"])
    targets[0]["external_result_sha256"] = _write(benchmark_path, benchmark)
    split_path = repo / "split.json"
    split = json.loads(split_path.read_text(encoding="utf-8"))
    split["contract_digest"] = "0" * 64
    targets[2]["split_contract_sha256"] = _write(split_path, split)
    result = run_independent_reproduction(plan, repo, data, "c" * 40, 789)
    contradictions = cast(list[str], result["contradictions"])
    assert any("duplicate ledger record identities" in item for item in contradictions)
    assert any("contract_digest content digest mismatch" in item for item in contradictions)


def test_source_identity_path_and_invocation_fail_closed(tmp_path: Path) -> None:
    plan, repo, data = _fixture(tmp_path)
    with pytest.raises(IndependentReproductionError, match="full Git SHA"):
        run_independent_reproduction(plan, repo, data, "short", 1)
    with pytest.raises(IndependentReproductionError, match="CI run"):
        run_independent_reproduction(plan, repo, data, "a" * 40, 0)
    targets = cast(list[dict[str, object]], plan.payload["targets"])
    targets[0]["external_result_sha256"] = "0" * 64
    with pytest.raises(IndependentReproductionError, match="SHA-256 mismatch"):
        run_independent_reproduction(plan, repo, data, "a" * 40, 1)
    targets[0]["external_result_sha256"] = hashlib.sha256(
        (data / "benchmark.json").read_bytes()
    ).hexdigest()
    targets[0]["external_result_path"] = "../outside.json"
    with pytest.raises(IndependentReproductionError, match="escapes"):
        run_independent_reproduction(plan, repo, data, "a" * 40, 1)


def test_result_writer_is_idempotent_and_immutable(tmp_path: Path) -> None:
    output = tmp_path / "result.json"
    result = {"status": "REPRODUCED"}
    write_independent_reproduction_result(output, result)
    write_independent_reproduction_result(output, result)
    with pytest.raises(IndependentReproductionError, match="different content"):
        write_independent_reproduction_result(output, {"status": "CONTRADICTED"})


def test_clean_room_numeric_and_comparison_helpers_cover_boundaries() -> None:
    assert subject._distribution([]) == {
        "n": 0,
        "minimum": None,
        "median": None,
        "p90": None,
        "maximum": None,
    }
    assert subject._distribution([0.0, 10.0])["p90"] == pytest.approx(9.0)
    contradictions: list[str] = []
    subject._compare_expected({}, {"missing": 1}, contradictions)
    subject._compare_value("mapping", {"a": 1}, {"b": 1}, contradictions)
    subject._compare_value("text", "actual", "expected", contradictions)
    assert contradictions == [
        "missing observation missing",
        "mapping keys differ",
        "text differs: 'actual' != 'expected'",
    ]


def test_clean_room_type_helpers_reject_malformed_values(tmp_path: Path) -> None:
    with pytest.raises(IndependentReproductionError, match="must be an object"):
        subject._object([], "row")
    with pytest.raises(IndependentReproductionError, match="must be an array"):
        subject._array({"items": "bad"}, "items")
    with pytest.raises(IndependentReproductionError, match="non-empty text"):
        subject._text({"field": ""}, "field")
    with pytest.raises(IndependentReproductionError, match="entries"):
        subject._string_item(1, "item")
    with pytest.raises(IndependentReproductionError, match="integer"):
        subject._integer({"count": True}, "count")
    with pytest.raises(IndependentReproductionError, match="boolean"):
        subject._boolean({"flag": 1}, "flag")
    with pytest.raises(IndependentReproductionError, match="finite numeric"):
        subject._number_value(float("nan"), "value")
    path = tmp_path / "source.json"
    digest = _write(path, {"ok": True})
    path.with_name("source.json.sha256").write_text("0" * 64, encoding="ascii")
    with pytest.raises(IndependentReproductionError, match="sidecar mismatch"):
        subject._verified_object(path, digest, "source")


def test_loader_rejects_invalid_json_shape_digest_and_policy_drift(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b"bad")
    with pytest.raises(IndependentReproductionError, match="valid UTF-8 JSON"):
        load_independent_reproduction_plan(invalid)
    scalar = tmp_path / "scalar.json"
    scalar.write_text("[]", encoding="utf-8")
    with pytest.raises(IndependentReproductionError, match="JSON object"):
        load_independent_reproduction_plan(scalar)
    payload = json.loads(PLAN.read_text(encoding="utf-8"))
    payload["task_id"] = "tampered"
    forged = tmp_path / "forged.json"
    forged.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(IndependentReproductionError, match="digest mismatch"):
        load_independent_reproduction_plan(forged)

    def reject(mutator: Callable[[dict[str, object]], None], match: str) -> None:
        value = json.loads(PLAN.read_text(encoding="utf-8"))
        mutator(value)
        value["plan_digest"] = _digest(
            {key: item for key, item in value.items() if key != "plan_digest"}
        )
        path = tmp_path / f"drift-{match.replace(' ', '-')}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        with pytest.raises(IndependentReproductionError, match=match):
            load_independent_reproduction_plan(path)

    reject(lambda value: value.update(task_id="R3-X"), "identity")
    reject(lambda value: value.update(extra=True), "fields mismatch")
    reject(lambda value: value.update(reproduction_id="changed"), "identifier")
    reject(lambda value: value.update(claim_boundary="changed"), "claim boundary")
    reject(
        lambda value: cast(dict[str, object], value["disclosure"]).update(
            upstream_results_were_inspected_before_freeze=False
        ),
        "disclosure",
    )
    reject(lambda value: value.update(targets=[]), "targets")
    reject(
        lambda value: cast(dict[str, object], value["independence_policy"]).update(
            same_function_stack_used=True
        ),
        "independence policy",
    )
    reject(
        lambda value: cast(dict[str, object], value["execution_policy"]).update(r3_325_rerun=True),
        "read-only",
    )
    reject(
        lambda value: cast(dict[str, object], value["execution_policy"]).update(
            contradictions="DISCARD_CONTRADICTIONS"
        ),
        "retention",
    )


def test_cli_reports_missing_data_root_before_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ROUTEMIND_DATA_ROOT", raising=False)
    with pytest.raises(SystemExit) as error:
        main(
            [
                "--plan",
                str(PLAN),
                "--repository-root",
                str(ROOT),
                "--implementation-revision",
                "a" * 40,
                "--implementation-ci-run",
                "1",
                "--output",
                str(tmp_path / "out.json"),
            ]
        )
    assert error.value.code == 2


def test_cli_returns_success_contradiction_and_validation_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_plan = IndependentReproductionPlan(
        {"reproduction_id": "fixture", "targets": []}, "f" * 64, "e" * 64
    )
    monkeypatch.setattr(subject, "load_independent_reproduction_plan", lambda _: fake_plan)
    written: list[dict[str, object]] = []
    monkeypatch.setattr(
        subject,
        "write_independent_reproduction_result",
        lambda _path, result: written.append(dict(result)),
    )

    def invoke() -> int:
        return main(
            [
                "--plan",
                str(PLAN),
                "--repository-root",
                str(ROOT),
                "--data-root",
                str(tmp_path),
                "--implementation-revision",
                "a" * 40,
                "--implementation-ci-run",
                "1",
                "--output",
                str(tmp_path / "out.json"),
            ]
        )

    monkeypatch.setattr(
        subject,
        "run_independent_reproduction",
        lambda *_args: {"overall_status": "REPRODUCED_WITH_NO_CONTRADICTIONS"},
    )
    assert invoke() == 0
    monkeypatch.setattr(
        subject,
        "run_independent_reproduction",
        lambda *_args: {"overall_status": "CONTRADICTIONS_RETAINED"},
    )
    assert invoke() == 3

    def fail(*_args: object) -> dict[str, object]:
        raise IndependentReproductionError("fixture failure")

    monkeypatch.setattr(subject, "run_independent_reproduction", fail)
    assert invoke() == 2
    captured = capsys.readouterr()
    assert "fixture failure" in captured.err
    assert len(written) == 2
