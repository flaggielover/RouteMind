"""Strict loader for the frozen R3-320 Statistical RouteBench protocol."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import cast

_SCHEMA = "routemind-statistical-routebench-protocol-v1"
_REVISION = re.compile(r"^[0-9a-f]{40}$")
_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_FROZEN_SHA256 = "a6dae9d55641ff7966ef4a50cc00a63da3e936620c3c48f23cd2c2ce039375b5"
_REGIMES = (
    "normal",
    "surge",
    "shortage",
    "merchant-delay",
    "travel-degradation",
    "location-staleness",
    "compute-budget",
    "queue-pressure",
)
_STREAMS = ("demand", "merchant", "courier", "traffic")
_SAFETY_METRICS = (
    "runtime_millis",
    "strategy_failure_rate",
    "fallback_rate",
    "timeout_rate",
)


class StatisticalRouteBenchProtocolError(ValueError):
    """Raised when the frozen R3-320 protocol is malformed or has drifted."""


@dataclass(frozen=True, slots=True)
class StatisticalRouteBenchProtocol:
    protocol_id: str
    manifest_sha256: str
    frozen_against_revision: str
    prerequisite_ci_run: int
    regime_ids: tuple[str, ...]
    common_streams: tuple[str, ...]
    pilot_replicates_per_regime: int
    maximum_confirmatory_pairs_per_regime: int
    number_of_confirmatory_tests: int


def load_statistical_routebench_protocol(path: Path) -> StatisticalRouteBenchProtocol:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise StatisticalRouteBenchProtocolError("protocol is unreadable") from error
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise StatisticalRouteBenchProtocolError("protocol is not valid UTF-8 JSON") from error
    root = _mapping(value, "protocol")
    _exact_keys(
        root,
        {
            "schema_version",
            "task_id",
            "protocol_id",
            "frozen_at_utc",
            "frozen_against_revision",
            "prerequisite_ci_run",
            "research",
            "arms",
            "primary_estimands",
            "scenario_design",
            "randomization",
            "prospective_power",
            "inference",
            "mandatory_safety_diagnostics",
            "outcome_handling",
            "stopping",
            "resource_envelope",
            "lineage",
            "supported_wording",
            "prohibited_wording",
        },
        "protocol",
    )
    _equal(root, "schema_version", _SCHEMA, "schema version")
    _equal(root, "task_id", "R3-320", "task identity")
    _equal(root, "protocol_id", "r3-320-statistical-routebench-v1", "protocol identity")
    if not _UTC.fullmatch(_string(root, "frozen_at_utc")):
        raise StatisticalRouteBenchProtocolError("freeze timestamp must be UTC RFC 3339 seconds")
    revision = _string(root, "frozen_against_revision")
    if not _REVISION.fullmatch(revision):
        raise StatisticalRouteBenchProtocolError("frozen revision must be a full Git SHA")
    prerequisite_ci_run = _positive_integer(root, "prerequisite_ci_run")

    _validate_research(_mapping(root.get("research"), "research"))
    _validate_arms(_mapping(root.get("arms"), "arms"))
    _validate_estimands(_mapping(root.get("primary_estimands"), "primary estimands"))
    regimes = _validate_scenarios(_mapping(root.get("scenario_design"), "scenario design"))
    randomization = _mapping(root.get("randomization"), "randomization")
    streams = _validate_randomization(randomization)
    power = _mapping(root.get("prospective_power"), "prospective power")
    maximum_pairs = _validate_power(power)
    inference = _mapping(root.get("inference"), "inference")
    tests = _validate_inference(inference)
    _validate_safety(_mapping(root.get("mandatory_safety_diagnostics"), "safety diagnostics"))
    _validate_outcomes(_mapping(root.get("outcome_handling"), "outcome handling"))
    _validate_stopping(_mapping(root.get("stopping"), "stopping"))
    _validate_resources(_mapping(root.get("resource_envelope"), "resource envelope"))
    _validate_lineage(_mapping(root.get("lineage"), "lineage"))
    if not _string(root, "supported_wording").startswith("This protocol prospectively fixes"):
        raise StatisticalRouteBenchProtocolError("supported wording drifted")
    if len(_strings(root.get("prohibited_wording"), "prohibited wording")) != 4:
        raise StatisticalRouteBenchProtocolError("prohibited wording set drifted")
    manifest_sha256 = sha256(raw).hexdigest()
    if manifest_sha256 != _FROZEN_SHA256:
        raise StatisticalRouteBenchProtocolError("protocol content identity drifted")

    return StatisticalRouteBenchProtocol(
        protocol_id=_string(root, "protocol_id"),
        manifest_sha256=manifest_sha256,
        frozen_against_revision=revision,
        prerequisite_ci_run=prerequisite_ci_run,
        regime_ids=regimes,
        common_streams=streams,
        pilot_replicates_per_regime=_integer(randomization, "pilot_replicates_per_regime"),
        maximum_confirmatory_pairs_per_regime=maximum_pairs,
        number_of_confirmatory_tests=tests,
    )


def _validate_research(value: Mapping[str, object]) -> None:
    _equal(value, "question_id", "RQ-B1", "research question")
    _equal(value, "hypothesis_id", "H1-B1", "hypothesis")
    if "risk-aware" not in _string(value, "question"):
        raise StatisticalRouteBenchProtocolError("research question drifted")
    if "-0.02" not in _string(value, "null") or "-0.02" not in _string(value, "alternative"):
        raise StatisticalRouteBenchProtocolError("assignment hypothesis margin drifted")


def _validate_arms(value: Mapping[str, object]) -> None:
    _exact_keys(value, {"candidate", "comparator"}, "arms")
    candidate = _mapping(value.get("candidate"), "candidate arm")
    comparator = _mapping(value.get("comparator"), "comparator arm")
    _equal(candidate, "strategy", "risk-aware", "candidate strategy")
    _equal(candidate, "version", "1.0.0", "candidate version")
    _equal(
        _mapping(candidate.get("parameters"), "candidate parameters"),
        None,
        {"distance": 1.0, "readiness": 0.5, "overtime": 2.0, "service_risk": 2.0, "balance": 0.5},
        "candidate parameters",
    )
    _equal(comparator, "strategy", "weighted-greedy", "comparator strategy")
    _equal(comparator, "version", "1.0.0", "comparator version")
    _equal(
        _mapping(comparator.get("parameters"), "comparator parameters"),
        None,
        {"distance_weight": 1.0},
        "comparator parameters",
    )


def _validate_estimands(value: Mapping[str, object]) -> None:
    _exact_keys(value, {"scenario_risk_index", "assignment_rate"}, "primary estimands")
    risk = _mapping(value.get("scenario_risk_index"), "risk estimand")
    assignment = _mapping(value.get("assignment_rate"), "assignment estimand")
    _equal(risk, "paired_difference", "candidate_minus_comparator", "risk contrast")
    _equal(risk, "direction", "lower_is_better", "risk direction")
    _equal(risk, "range", [0.0, 1.0], "risk range")
    _equal(risk, "unassigned_timeout_or_strategy_failure_value", 1.0, "risk failure value")
    formula = _string(risk, "assigned_request_formula")
    if formula != "0.5 * selected_service_risk + 0.5 * selected_overtime_risk":
        raise StatisticalRouteBenchProtocolError("independent risk formula drifted")
    if "strategy scores" not in _string(risk, "independence_rule"):
        raise StatisticalRouteBenchProtocolError("risk independence rule drifted")
    _equal(assignment, "paired_difference", "candidate_minus_comparator", "assignment contrast")
    _equal(assignment, "noninferiority_margin", -0.02, "assignment margin")
    _equal(assignment, "denominator", "every_preregistered_request", "assignment denominator")


def _validate_scenarios(value: Mapping[str, object]) -> tuple[str, ...]:
    _equal(value, "generator_version", "r3-b-stress-generator-v1", "generator version")
    _equal(value, "ticks_per_hour", 60, "tick rate")
    _equal(value, "horizon_ticks", 360, "horizon")
    base = _mapping(value.get("base"), "scenario base")
    _equal(base, "demand_rate_per_hour", 12.0, "base demand")
    _equal(base, "courier_count", 12, "base supply")
    regimes = _sequence(value.get("regimes"), "regimes")
    if len(regimes) != 8:
        raise StatisticalRouteBenchProtocolError("stress matrix must contain eight regimes")
    mapped = tuple(_mapping(item, "regime") for item in regimes)
    ids = tuple(_string(item, "regime_id") for item in mapped)
    if ids != _REGIMES or len(set(ids)) != len(ids):
        raise StatisticalRouteBenchProtocolError("stress regime identities or order drifted")
    expected_changes = {
        "normal": ("demand_multiplier", 1.0),
        "surge": ("demand_multiplier", 2.0),
        "shortage": ("supply_multiplier", 0.5),
        "merchant-delay": ("merchant_delay_ticks", 5),
        "travel-degradation": ("traffic_multiplier", 1.75),
        "location-staleness": ("location_staleness_seconds", 300),
        "compute-budget": ("decision_budget_millis", 5.0),
        "queue-pressure": ("merchant_queue_capacity", 4),
    }
    for regime in mapped:
        key, expected = expected_changes[_string(regime, "regime_id")]
        _equal(regime, key, expected, f"{_string(regime, 'regime_id')} perturbation")
    return ids


def _validate_randomization(value: Mapping[str, object]) -> tuple[str, ...]:
    _equal(value, "pairing_unit", "regime_id_plus_replicate", "pairing unit")
    streams = _strings(value.get("common_streams"), "common streams")
    if streams != _STREAMS:
        raise StatisticalRouteBenchProtocolError("common stream ownership drifted")
    _equal(value, "stream_ownership_task", "R3-321", "stream ownership task")
    if not _string(value, "seed_derivation").startswith("SHA256(protocol_id|"):
        raise StatisticalRouteBenchProtocolError("seed derivation drifted")
    _equal(value, "arm_order", "alternate_by_replicate_parity", "arm order")
    _equal(value, "pilot_replicates_per_regime", 8, "pilot count")
    _equal(value, "pilot_replicate_range", [0, 7], "pilot range")
    _equal(value, "confirmatory_replicate_start", 1000, "confirmatory seed boundary")
    _equal(value, "pilot_seeds_must_not_enter_confirmatory_analysis", True, "pilot separation")
    return streams


def _validate_power(value: Mapping[str, object]) -> int:
    _equal(value, "task", "R3-323", "power task")
    _equal(value, "pilot_only_for_variance", True, "pilot role")
    _equal(value, "minimum_detectable_risk_difference", -0.02, "risk MDE")
    _equal(value, "assignment_noninferiority_margin", -0.02, "power assignment margin")
    _equal(value, "familywise_alpha", 0.05, "alpha")
    _equal(value, "target_power", 0.8, "power")
    _equal(value, "minimum_confirmatory_pairs_per_regime", 20, "minimum pairs")
    maximum = _integer(value, "maximum_confirmatory_pairs_per_regime")
    if maximum != 200:
        raise StatisticalRouteBenchProtocolError("maximum confirmatory pairs drifted")
    _equal(value, "round_up_to_pairs", 4, "pair rounding")
    if "underpowered" not in _string(value, "underpowered_rule"):
        raise StatisticalRouteBenchProtocolError("underpowered rule drifted")
    return maximum


def _validate_inference(value: Mapping[str, object]) -> int:
    _equal(value, "analysis_unit", "paired_regime_seed_difference", "analysis unit")
    _equal(value, "primary_location", "arithmetic_mean", "primary location")
    _equal(value, "interval", "two-sided_student_t_95_percent_on_paired_differences", "interval")
    _equal(value, "directional_tests", "one-sided_paired_t", "directional tests")
    _equal(value, "effect_size", "paired_cohens_dz", "effect size")
    _equal(value, "multiplicity", "holm_bonferroni_familywise", "multiplicity")
    tests = _integer(value, "number_of_confirmatory_tests")
    if tests != 16:
        raise StatisticalRouteBenchProtocolError("confirmatory test family drifted")
    if not _string(value, "overall_support_rule").startswith("Every regime must pass"):
        raise StatisticalRouteBenchProtocolError("overall support rule drifted")
    if len(_strings(value.get("sensitivity"), "sensitivity analyses")) != 3:
        raise StatisticalRouteBenchProtocolError("sensitivity set drifted")
    _equal(value, "sensitivity_cannot_replace_primary", True, "sensitivity role")
    return tests


def _validate_safety(value: Mapping[str, object]) -> None:
    if _strings(value.get("metrics"), "safety metrics") != _SAFETY_METRICS:
        raise StatisticalRouteBenchProtocolError("mandatory safety metrics drifted")
    if "every event identity" not in _string(value, "reporting"):
        raise StatisticalRouteBenchProtocolError("safety reporting rule drifted")


def _validate_outcomes(value: Mapping[str, object]) -> None:
    retained = _strings(value.get("legitimate_outcomes_never_excluded"), "retained outcomes")
    required = {
        "bad_seed_result",
        "unassigned",
        "timeout",
        "strategy_failure",
        "fallback",
        "null_effect",
        "unfavorable_effect",
    }
    if set(retained) != required:
        raise StatisticalRouteBenchProtocolError("retained outcome policy drifted")
    allowed = _strings(value.get("allowed_pair_exclusions"), "allowed exclusions")
    if len(allowed) != 4 or any("seed" in item for item in allowed):
        raise StatisticalRouteBenchProtocolError("pair exclusion policy drifted")
    scoring = _mapping(value.get("strategy_failure_scoring"), "failure scoring")
    _equal(scoring, None, {"scenario_risk_index": 1.0, "assignment_rate": 0.0}, "failure scoring")
    if "Do not impute" not in _string(value, "missing_pair_rule"):
        raise StatisticalRouteBenchProtocolError("missing-pair rule drifted")


def _validate_stopping(value: Mapping[str, object]) -> None:
    _equal(value, "desired_result_stopping_allowed", False, "desired-result stopping")
    _equal(value, "interim_efficacy_looks", 0, "interim looks")
    if "eight_complete_pairs" not in _string(value, "pilot_stop"):
        raise StatisticalRouteBenchProtocolError("pilot stopping rule drifted")
    if len(_strings(value.get("early_stop_reasons"), "early-stop reasons")) != 5:
        raise StatisticalRouteBenchProtocolError("early-stop reasons drifted")


def _validate_resources(value: Mapping[str, object]) -> None:
    _equal(value, "execution", "local_only", "execution boundary")
    _equal(value, "threads_per_arm", 1, "thread limit")
    _equal(value, "arm_wall_timeout_seconds", 30, "arm timeout")
    _equal(value, "pilot_arm_runs", 128, "pilot arm runs")
    _equal(value, "maximum_confirmatory_arm_runs", 3200, "campaign arm runs")
    _equal(value, "external_cost_usd", 0.0, "external cost")
    _equal(value, "material_execution_task", "R3-325", "material task")


def _validate_lineage(value: Mapping[str, object]) -> None:
    required = _strings(value.get("required"), "lineage fields")
    if len(required) != 14 or len(set(required)) != len(required):
        raise StatisticalRouteBenchProtocolError("lineage field set drifted")
    _equal(
        value,
        "large_artifact_boundary",
        "ROUTEMIND_DATA_ROOT/experiments/r3/R3-325",
        "artifact boundary",
    )
    prohibited_until = _strings(value.get("campaign_execution_prohibited_until"), "campaign gates")
    if len(prohibited_until) != 5 or prohibited_until[:4] != (
        "R3-321 passed",
        "R3-322 passed",
        "R3-323 passed",
        "R3-324 passed",
    ):
        raise StatisticalRouteBenchProtocolError("campaign prerequisite gates drifted")


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise StatisticalRouteBenchProtocolError(f"{label} must be an object")
    return cast(Mapping[str, object], value)


def _sequence(value: object, label: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise StatisticalRouteBenchProtocolError(f"{label} must be an array")
    return cast(Sequence[object], value)


def _strings(value: object, label: str) -> tuple[str, ...]:
    values = _sequence(value, label)
    if not all(isinstance(item, str) and item.strip() for item in values):
        raise StatisticalRouteBenchProtocolError(f"{label} must contain nonblank strings")
    return cast(tuple[str, ...], tuple(values))


def _string(value: Mapping[str, object], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise StatisticalRouteBenchProtocolError(f"{key} must be a nonblank string")
    return item


def _integer(value: Mapping[str, object], key: str) -> int:
    item = value.get(key)
    if not isinstance(item, int) or isinstance(item, bool):
        raise StatisticalRouteBenchProtocolError(f"{key} must be an integer")
    return item


def _positive_integer(value: Mapping[str, object], key: str) -> int:
    item = _integer(value, key)
    if item <= 0:
        raise StatisticalRouteBenchProtocolError(f"{key} must be positive")
    return item


def _equal(value: Mapping[str, object], key: str | None, expected: object, label: str) -> None:
    actual: object = value if key is None else value.get(key)
    if actual != expected or type(actual) is not type(expected):
        raise StatisticalRouteBenchProtocolError(f"{label} drifted")


def _exact_keys(value: Mapping[str, object], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise StatisticalRouteBenchProtocolError(f"{label} fields drifted")


__all__ = [
    "StatisticalRouteBenchProtocol",
    "StatisticalRouteBenchProtocolError",
    "load_statistical_routebench_protocol",
]
