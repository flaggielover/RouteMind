"""Standard-library-only clean-room checker for major Round 3 results."""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

_SCHEMA = "routemind-independent-reproduction-v1"
_RESULT_SCHEMA = "routemind-independent-reproduction-result-v1"
_TARGETS = ("R3-316", "R3-327", "R3-336", "R3-349")
_CLAIM_BOUNDARY = "INDEPENDENT_REPRODUCTION_IS_CLAIM_INPUT_NOT_CI_OR_NEW_EFFECT_EVIDENCE"
_ALLOWED_IMPORT_ROOTS = (
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
)
JsonObject = dict[str, object]


class IndependentReproductionError(ValueError):
    """Raised when the clean-room plan, sources, or output boundary is invalid."""


@dataclass(frozen=True, slots=True)
class IndependentReproductionPlan:
    payload: Mapping[str, object]
    plan_digest: str
    manifest_sha256: str


def load_independent_reproduction_plan(path: Path | str) -> IndependentReproductionPlan:
    plan_path = Path(path).expanduser().resolve()
    raw, parsed = _read_object(plan_path, "independent reproduction plan")
    digest = _text(parsed, "plan_digest")
    unsigned = dict(parsed)
    del unsigned["plan_digest"]
    if _canonical_digest(unsigned) != digest:
        raise IndependentReproductionError("independent reproduction plan digest mismatch")
    _validate_plan(parsed)
    return IndependentReproductionPlan(parsed, digest, sha256(raw).hexdigest())


def run_independent_reproduction(
    plan: IndependentReproductionPlan,
    repository_root: Path | str,
    data_root: Path | str,
    implementation_revision: str,
    implementation_ci_run: int,
) -> JsonObject:
    if len(implementation_revision) != 40 or any(
        char not in "0123456789abcdef" for char in implementation_revision
    ):
        raise IndependentReproductionError("implementation revision must be a full Git SHA")
    if isinstance(implementation_ci_run, bool) or implementation_ci_run <= 0:
        raise IndependentReproductionError("implementation CI run must be positive")
    repo = Path(repository_root).expanduser().resolve()
    data = Path(data_root).expanduser().resolve()
    targets = {
        _text(target, "task_id"): target
        for target in (_object(item, "target") for item in _array(plan.payload, "targets"))
    }
    results = (
        _check_benchmark(targets["R3-316"], repo, data),
        _check_statistical(targets["R3-327"], data),
        _check_twin(targets["R3-336"], repo),
        _check_rads(targets["R3-349"], repo, data),
    )
    contradictions = tuple(
        f"{result['task_id']}:{item}"
        for result in results
        for item in _string_array(result, "contradictions")
    )
    core: JsonObject = {
        "schema_version": _RESULT_SCHEMA,
        "task_id": "R3-356",
        "reproduction_id": _text(plan.payload, "reproduction_id"),
        "plan_digest": plan.plan_digest,
        "implementation_revision": implementation_revision,
        "implementation_ci_run": implementation_ci_run,
        "checker_environment": {
            "implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "platform": sys.platform,
        },
        "independence": {
            "implementation": "STANDARD_LIBRARY_ONLY_ALTERNATE_CHECKER",
            "same_function_stack_used": False,
            "imports_original_analysis_modules": False,
        },
        "target_results": list(results),
        "contradictions": list(contradictions),
        "overall_status": (
            "REPRODUCED_WITH_NO_CONTRADICTIONS" if not contradictions else "CONTRADICTIONS_RETAINED"
        ),
        "claim_boundary": _CLAIM_BOUNDARY,
    }
    return {**core, "result_digest": _canonical_digest(core)}


def write_independent_reproduction_result(path: Path | str, result: Mapping[str, object]) -> None:
    output = Path(path).expanduser().resolve()
    encoded = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if output.exists():
        if output.read_bytes() != encoded:
            raise IndependentReproductionError(
                "reproduction result already exists with different content"
            )
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(encoded)


def _check_benchmark(target: Mapping[str, object], repo: Path, data: Path) -> JsonObject:
    contradictions: list[str] = []
    source = _verified_object(
        _resolve_below(data, _text(target, "external_result_path")),
        _text(target, "external_result_sha256"),
        "R3-316 external result",
    )
    reported = _verified_object(
        _resolve_below(repo, _text(target, "reported_result_path")),
        _text(target, "reported_result_sha256"),
        "R3-316 committed result",
    )
    ledger = tuple(
        _object(item, "R3-316 ledger row") for item in _array(source, "all_outcome_ledger")
    )
    source_rows = tuple(row for row in ledger if row.get("analysis_domain") == "SOURCE_DOUBLE_BKS")
    derived_rows = tuple(
        row
        for row in ledger
        if row.get("analysis_domain") == "DERIVED_CONSERVATIVE_INTEGER_OPTIMUM"
    )
    observations: JsonObject = {
        "record_count": len(ledger),
        "unique_record_count": len({_text(row, "record_id") for row in ledger}),
        "source_records": len(source_rows),
        "derived_records": len(derived_rows),
        "source_outcomes": dict(Counter(_text(row, "outcome") for row in source_rows)),
        "reference_comparisons": dict(
            Counter(_text(row, "reference_comparison") for row in source_rows)
        ),
        "vehicle_gap_percent": _distribution(
            [
                _number_value(row.get("vehicle_gap_percent"), "vehicle gap")
                for row in source_rows
                if row.get("vehicle_gap_percent") is not None
            ]
        ),
        "same_vehicle_distance_gap_percent": _distribution(
            [
                _number_value(row.get("same_vehicle_distance_gap_percent"), "distance gap")
                for row in source_rows
                if row.get("same_vehicle_distance_gap_percent") is not None
            ]
        ),
        "transformed_exact_gap_percent": _distribution(
            [
                _number_value(row.get("transformed_exact_gap_percent"), "exact gap")
                for row in derived_rows
            ]
        ),
        "statistical_disposition": _text(source, "statistical_disposition"),
        "claim_disposition": _text(source, "claim_disposition"),
    }
    expected = _object(target.get("expected"), "R3-316 expected")
    _compare_expected(observations, expected, contradictions)
    reported_source = _object(reported.get("source_double_bks"), "reported source result")
    reported_exact = _object(
        reported.get("derived_conservative_integer_optimum"), "reported exact result"
    )
    _compare_value(
        "reported.vehicle_gap_percent",
        observations["vehicle_gap_percent"],
        reported_source.get("vehicle_gap_percent"),
        contradictions,
    )
    _compare_value(
        "reported.same_vehicle_distance_gap_percent",
        observations["same_vehicle_distance_gap_percent"],
        reported_source.get("same_vehicle_distance_gap_percent"),
        contradictions,
    )
    _compare_value(
        "reported.transformed_exact_gap_percent",
        observations["transformed_exact_gap_percent"],
        reported_exact.get("transformed_exact_gap_percent"),
        contradictions,
    )
    if observations["record_count"] != observations["unique_record_count"]:
        contradictions.append("duplicate ledger record identities")
    return _target_result(target, observations, contradictions)


def _check_statistical(target: Mapping[str, object], data: Path) -> JsonObject:
    contradictions: list[str] = []
    artifact = _verified_object(
        _resolve_below(data, _text(target, "external_result_path")),
        _text(target, "external_result_sha256"),
        "R3-327 statistical report",
    )
    report = _object(artifact.get("report"), "statistical report body")
    cells = tuple(_object(item, "statistical cell") for item in _array(report, "cells"))
    expected = _object(target.get("expected"), "R3-327 expected")
    regimes = tuple(_string_array(expected, "regimes"))
    metrics = tuple(_string_array(expected, "metrics"))
    cell_ids = tuple((_text(cell, "regime_id"), _text(cell, "metric_id")) for cell in cells)
    expected_ids = tuple((regime, metric) for regime in regimes for metric in metrics)
    non_estimable_set = {
        _text(cell, "regime_id")
        for cell in cells
        if cell.get("metric_id") == "assignment_rate" and cell.get("status") == "NON_ESTIMABLE"
    }
    non_estimable = [regime for regime in regimes if regime in non_estimable_set]
    pair_shapes_ok = all(
        _integer(cell, "n") == _integer(expected, "pairs_per_cell")
        and len(_array(cell, "pair_seeds")) == _integer(expected, "pairs_per_cell")
        for cell in cells
    )
    stream_names = set(_string_array(expected, "stream_names"))
    streams_ok = all(
        {
            _text(_object(stream, "stream"), "stream_name")
            for pair in _array(cell, "pair_seeds")
            for stream in _array(_object(pair, "pair seed"), "streams")
        }
        == stream_names
        for cell in cells
    )
    multiplicity = _object(report.get("multiplicity"), "multiplicity")
    tests = tuple(_object(item, "multiplicity test") for item in _array(multiplicity, "tests"))
    no_inference = all(
        item.get("raw_p_value") is None
        and item.get("adjusted_p_value") is None
        and item.get("rejected") is False
        for item in tests
    )
    diagnostics = _object(report.get("diagnostics"), "diagnostics")
    observations: JsonObject = {
        "report_digest": _canonical_digest(report),
        "artifact_report_digest": _text(artifact, "report_digest"),
        "cell_count": len(cells),
        "cell_identities_complete": len(set(cell_ids)) == len(expected_ids)
        and set(cell_ids) == set(expected_ids),
        "pairs_and_streams_complete": pair_shapes_ok and streams_ok,
        "non_estimable_assignment_regimes": non_estimable,
        "multiplicity_disposition": _text(multiplicity, "disposition"),
        "multiplicity_tests": len(tests),
        "confirmatory_inference_absent": no_inference,
        "arm_count": _integer(diagnostics, "arm_count"),
        "failure_count": _integer(diagnostics, "failure_count"),
        "fallback_count": _integer(diagnostics, "fallback_count"),
        "timeout_count": _integer(diagnostics, "timeout_count"),
        "statistical_disposition": "S-FAIL",
        "claim_disposition": "C-NO-CLAIM",
    }
    configuration_keys = {"regimes", "metrics", "pairs_per_cell", "stream_names"}
    expected_comparison = {
        **{key: value for key, value in expected.items() if key not in configuration_keys},
        "cell_count": len(expected_ids),
        "cell_identities_complete": True,
        "pairs_and_streams_complete": True,
        "artifact_report_digest": expected["report_digest"],
        "multiplicity_tests": len(expected_ids),
        "confirmatory_inference_absent": True,
    }
    _compare_expected(observations, expected_comparison, contradictions)
    return _target_result(target, observations, contradictions)


def _check_twin(target: Mapping[str, object], repo: Path) -> JsonObject:
    contradictions: list[str] = []
    split = _verified_object(
        _resolve_below(repo, _text(target, "split_contract_path")),
        _text(target, "split_contract_sha256"),
        "R3-330 split contract",
    )
    report = _verified_object(
        _resolve_below(repo, _text(target, "report_plan_path")),
        _text(target, "report_plan_sha256"),
        "R3-336 report plan",
    )
    _check_embedded_digest(split, "contract_digest", contradictions)
    _check_embedded_digest(report, "plan_digest", contradictions)
    availability = _object(split.get("data_availability"), "Twin data availability")
    splits = _object(split.get("splits"), "Twin splits")
    calibration = _object(splits.get("calibration"), "calibration split")
    held_out = _object(splits.get("held_out"), "held-out split")
    observations: JsonObject = {
        "observed_record_count": _integer(availability, "observed_record_count"),
        "calibration_record_count": _integer(calibration, "record_count"),
        "held_out_record_count": _integer(held_out, "record_count"),
        "status": _text(availability, "status"),
        "thresholds": "NOT_EVALUATED_NO_DATA",
        "unsupported_regimes": "NOT_ANALYZED_NO_DATA",
        "sensitivity": "NOT_RUN_NO_DATA",
        "data_limits": "INSUFFICIENT_DATA",
        "claim_status": _text(_object(report.get("claim_policy"), "claim policy"), "status"),
    }
    _compare_expected(
        observations, _object(target.get("expected"), "R3-336 expected"), contradictions
    )
    return _target_result(target, observations, contradictions)


def _check_rads(target: Mapping[str, object], repo: Path, data: Path) -> JsonObject:
    contradictions: list[str] = []
    plan = _verified_object(
        _resolve_below(repo, _text(target, "robustness_plan_path")),
        _text(target, "robustness_plan_sha256"),
        "R3-349 robustness plan",
    )
    _check_embedded_digest(plan, "plan_digest", contradictions)
    artifact = _verified_object(
        _resolve_below(data, _text(target, "external_result_path")),
        _text(target, "external_result_sha256"),
        "R3-325 statistical report",
    )
    report = _object(artifact.get("report"), "R3-325 report body")
    cells = tuple(_object(item, "RADS source cell") for item in _array(report, "cells"))
    regimes = {_text(cell, "regime_id") for cell in cells}
    strategy_ids = sorted(
        _object(
            _object(report.get("diagnostics"), "diagnostics").get("by_strategy"),
            "strategy diagnostics",
        )
    )
    expected = _object(target.get("expected"), "R3-349 expected")
    source_axes = [
        "seeds",
        "demand",
        "supply",
        "merchant_delay",
        "traffic",
        "location_staleness",
        "compute_constraints",
    ]
    absent_variants = tuple(_string_array(expected, "absent_variant_identities"))
    observations: JsonObject = {
        "source_regime_axes": source_axes,
        "unsupported_axes": ["location_noise"] if "location-noise" not in regimes else [],
        "pairs_per_existing_regime": min(_integer(cell, "n") for cell in cells),
        "minimum_pairs_per_axis_level": _integer(
            _object(plan.get("analysis_plan"), "analysis plan"), "minimum_pairs_per_axis_level"
        ),
        "observed_strategy_identities": strategy_ids,
        "absent_variant_identities": [
            identity for identity in absent_variants if identity not in strategy_ids
        ],
        "status": "INSUFFICIENT_DATA",
        "broad_claim_status": "PROHIBITED_NO_CROSS_REGIME_EVIDENCE",
        "claim_disposition": "C-NO-CLAIM",
    }
    _compare_expected(observations, expected, contradictions)
    return _target_result(target, observations, contradictions)


def _target_result(
    target: Mapping[str, object], observations: Mapping[str, object], contradictions: Sequence[str]
) -> JsonObject:
    return {
        "task_id": _text(target, "task_id"),
        "checker": _text(target, "checker"),
        "status": "REPRODUCED" if not contradictions else "CONTRADICTED",
        "observations": dict(observations),
        "contradictions": list(contradictions),
    }


def _distribution(values: Sequence[float]) -> JsonObject:
    ordered = sorted(values)
    if not ordered:
        return {"n": 0, "minimum": None, "median": None, "p90": None, "maximum": None}
    return {
        "n": len(ordered),
        "minimum": ordered[0],
        "median": _type7(ordered, 0.5),
        "p90": _type7(ordered, 0.9),
        "maximum": ordered[-1],
    }


def _type7(ordered: Sequence[float], probability: float) -> float:
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    fraction = position - lower
    return ordered[lower] + fraction * (ordered[min(lower + 1, len(ordered) - 1)] - ordered[lower])


def _compare_expected(
    actual: Mapping[str, object], expected: Mapping[str, object], contradictions: list[str]
) -> None:
    for key, expected_value in expected.items():
        if key not in actual:
            contradictions.append(f"missing observation {key}")
        else:
            _compare_value(key, actual[key], expected_value, contradictions)


def _compare_value(label: str, actual: object, expected: object, contradictions: list[str]) -> None:
    if isinstance(actual, Mapping) and isinstance(expected, Mapping):
        if set(actual) != set(expected):
            contradictions.append(f"{label} keys differ")
            return
        for key in expected:
            _compare_value(f"{label}.{key}", actual[key], expected[key], contradictions)
        return
    if (
        isinstance(actual, (int, float))
        and not isinstance(actual, bool)
        and isinstance(expected, (int, float))
        and not isinstance(expected, bool)
    ):
        if not math.isclose(float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-12):
            contradictions.append(f"{label} differs: {actual!r} != {expected!r}")
        return
    if actual != expected:
        contradictions.append(f"{label} differs: {actual!r} != {expected!r}")


def _check_embedded_digest(
    value: Mapping[str, object], key: str, contradictions: list[str]
) -> None:
    unsigned = dict(value)
    expected = _text(unsigned, key)
    del unsigned[key]
    if _canonical_digest(unsigned) != expected:
        contradictions.append(f"{key} content digest mismatch")


def _validate_plan(value: Mapping[str, object]) -> None:
    required = {
        "schema_version",
        "task_id",
        "reproduction_id",
        "frozen_at_utc",
        "disclosure",
        "independence_policy",
        "targets",
        "execution_policy",
        "claim_boundary",
        "plan_digest",
    }
    if set(value) != required:
        raise IndependentReproductionError("independent reproduction plan fields mismatch")
    if _text(value, "schema_version") != _SCHEMA or _text(value, "task_id") != "R3-356":
        raise IndependentReproductionError("independent reproduction identity is unsupported")
    if _text(value, "reproduction_id") != "r3-356-independent-reproduction-v1":
        raise IndependentReproductionError("independent reproduction identifier is not frozen")
    if _text(value, "claim_boundary") != _CLAIM_BOUNDARY:
        raise IndependentReproductionError("independent reproduction claim boundary is missing")
    _text(value, "frozen_at_utc")
    disclosure = _object(value.get("disclosure"), "disclosure")
    if not _boolean(disclosure, "upstream_results_existed_before_freeze") or not _boolean(
        disclosure, "upstream_results_were_inspected_before_freeze"
    ):
        raise IndependentReproductionError("retrospective disclosure must remain explicit")
    independence = _object(value.get("independence_policy"), "independence policy")
    if (
        _text(independence, "implementation") != "STANDARD_LIBRARY_ONLY_ALTERNATE_CHECKER"
        or _boolean(independence, "same_function_stack_used")
        or _boolean(independence, "imports_original_analysis_modules")
        or tuple(_string_array(independence, "allowed_import_roots")) != _ALLOWED_IMPORT_ROOTS
    ):
        raise IndependentReproductionError("clean-room independence policy drifted")
    targets = tuple(_object(item, "target") for item in _array(value, "targets"))
    if tuple(_text(target, "task_id") for target in targets) != _TARGETS:
        raise IndependentReproductionError("independent reproduction targets are not frozen")
    execution = _object(value.get("execution_policy"), "execution policy")
    if any(
        _boolean(execution, key)
        for key in (
            "material_run_before_green_implementation_ci",
            "r3_325_rerun",
            "source_writes",
            "synthetic_substitution",
        )
    ):
        raise IndependentReproductionError(
            "independent reproduction execution must remain read-only"
        )
    if _text(execution, "contradictions") != "RETAIN_AND_FAIL_REPRODUCTION":
        raise IndependentReproductionError("contradiction retention policy drifted")


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, allow_nan=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _verified_object(path: Path, expected_sha: str, label: str) -> JsonObject:
    raw, parsed = _read_object(path, label)
    if sha256(raw).hexdigest() != expected_sha:
        raise IndependentReproductionError(f"{label} SHA-256 mismatch")
    sidecar = path.with_name(path.name + ".sha256")
    if sidecar.exists() and sidecar.read_text(encoding="ascii").strip() != expected_sha:
        raise IndependentReproductionError(f"{label} sidecar mismatch")
    return parsed


def _read_object(path: Path, label: str) -> tuple[bytes, JsonObject]:
    try:
        raw = path.read_bytes()
        value: Any = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IndependentReproductionError(f"{label} is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise IndependentReproductionError(f"{label} must be a JSON object")
    return raw, value


def _resolve_below(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise IndependentReproductionError("source path escapes its declared root") from exc
    return candidate


def _object(value: object, label: str) -> JsonObject:
    if not isinstance(value, Mapping):
        raise IndependentReproductionError(f"{label} must be an object")
    return dict(value)


def _array(value: Mapping[str, object], key: str) -> Sequence[object]:
    selected = value.get(key)
    if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes, bytearray)):
        raise IndependentReproductionError(f"{key} must be an array")
    return selected


def _string_array(value: Mapping[str, object], key: str) -> tuple[str, ...]:
    return tuple(_string_item(item, key) for item in _array(value, key))


def _text(value: Mapping[str, object], key: str) -> str:
    selected = value.get(key)
    if not isinstance(selected, str) or not selected.strip() or len(selected) > 2048:
        raise IndependentReproductionError(f"{key} must be non-empty text")
    return selected


def _string_item(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IndependentReproductionError(f"{label} entries must be non-empty text")
    return value


def _integer(value: Mapping[str, object], key: str) -> int:
    selected = value.get(key)
    if isinstance(selected, bool) or not isinstance(selected, int):
        raise IndependentReproductionError(f"{key} must be an integer")
    return selected


def _boolean(value: Mapping[str, object], key: str) -> bool:
    selected = value.get(key)
    if not isinstance(selected, bool):
        raise IndependentReproductionError(f"{key} must be boolean")
    return selected


def _number_value(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise IndependentReproductionError(f"{label} must be finite numeric data")
    return float(value)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the R3-356 clean-room reproduction")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, default=os.environ.get("ROUTEMIND_DATA_ROOT"))
    parser.add_argument("--implementation-revision", required=True)
    parser.add_argument("--implementation-ci-run", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.data_root is None:
        parser.error("--data-root or ROUTEMIND_DATA_ROOT is required")
    try:
        plan = load_independent_reproduction_plan(args.plan)
        result = run_independent_reproduction(
            plan,
            args.repository_root,
            args.data_root,
            args.implementation_revision,
            args.implementation_ci_run,
        )
        write_independent_reproduction_result(args.output, result)
    except IndependentReproductionError as exc:
        print(f"R3-356 independent reproduction failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["overall_status"] == "REPRODUCED_WITH_NO_CONTRADICTIONS" else 3


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "IndependentReproductionError",
    "IndependentReproductionPlan",
    "load_independent_reproduction_plan",
    "main",
    "run_independent_reproduction",
    "write_independent_reproduction_result",
]
