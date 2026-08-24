from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from routemind_compute.application.statistical_routebench_protocol import (
    StatisticalRouteBenchProtocolError,
    load_statistical_routebench_protocol,
)

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = (
    ROOT
    / "docs"
    / "research"
    / "r3"
    / "manifests"
    / "statistical-routebench"
    / "statistical-routebench-v1.json"
)


def test_frozen_protocol_loads_with_content_identity_and_prerequisites() -> None:
    protocol = load_statistical_routebench_protocol(PROTOCOL)

    assert protocol.protocol_id == "r3-320-statistical-routebench-v1"
    assert protocol.manifest_sha256 == hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    assert protocol.frozen_against_revision == "c0967c1208be2249e672dc5ca9b8a32a687d4110"
    assert protocol.prerequisite_ci_run == 32711507127
    assert protocol.regime_ids == (
        "normal",
        "surge",
        "shortage",
        "merchant-delay",
        "travel-degradation",
        "location-staleness",
        "compute-budget",
        "queue-pressure",
    )
    assert protocol.common_streams == ("demand", "merchant", "courier", "traffic")
    assert protocol.pilot_replicates_per_regime == 8
    assert protocol.maximum_confirmatory_pairs_per_regime == 200
    assert protocol.number_of_confirmatory_tests == 16


@pytest.mark.parametrize(
    ("path", "replacement", "message"),
    (
        (("schema_version",), "v2", "schema version"),
        (("task_id",), "R3-X", "task identity"),
        (("protocol_id",), "other", "protocol identity"),
        (("frozen_at_utc",), "2026-08-24", "freeze timestamp"),
        (("frozen_against_revision",), "short", "full Git SHA"),
        (("prerequisite_ci_run",), 0, "must be positive"),
        (("prerequisite_ci_run",), True, "must be an integer"),
        (("research", "question_id"), "RQ-X", "research question"),
        (("research", "hypothesis_id"), "H1-X", "hypothesis"),
        (("research", "question"), "other", "research question drifted"),
        (("research", "null"), "other", "hypothesis margin"),
        (("arms", "candidate", "strategy"), "weighted-greedy", "candidate strategy"),
        (("arms", "candidate", "parameters", "service_risk"), 1.0, "candidate parameters"),
        (("arms", "comparator", "parameters", "distance_weight"), 2.0, "comparator parameters"),
        (("primary_estimands", "scenario_risk_index", "direction"), "higher", "risk direction"),
        (
            ("primary_estimands", "scenario_risk_index", "assigned_request_formula"),
            "strategy_score",
            "independent risk formula",
        ),
        (
            ("primary_estimands", "scenario_risk_index", "independence_rule"),
            "use a stable metric",
            "risk independence rule",
        ),
        (
            (
                "primary_estimands",
                "scenario_risk_index",
                "unassigned_timeout_or_strategy_failure_value",
            ),
            0.0,
            "risk failure value",
        ),
        (
            ("primary_estimands", "assignment_rate", "noninferiority_margin"),
            -0.01,
            "assignment margin",
        ),
        (("scenario_design", "horizon_ticks"), 10, "horizon"),
        (("scenario_design", "regimes"), [], "eight regimes"),
        (("scenario_design", "regimes", 1, "regime_id"), "normal", "stress regime"),
        (("scenario_design", "regimes", 2, "supply_multiplier"), 0.75, "shortage perturbation"),
        (("randomization", "common_streams"), ["demand"], "common stream"),
        (("randomization", "seed_derivation"), "random", "seed derivation"),
        (("randomization", "pilot_replicates_per_regime"), 7, "pilot count"),
        (("randomization", "confirmatory_replicate_start"), 8, "confirmatory seed boundary"),
        (("prospective_power", "minimum_detectable_risk_difference"), -0.01, "risk MDE"),
        (("prospective_power", "underpowered_rule"), "raise cap", "underpowered rule"),
        (
            ("prospective_power", "maximum_confirmatory_pairs_per_regime"),
            201,
            "maximum confirmatory",
        ),
        (("inference", "interval"), "bootstrap", "interval"),
        (("inference", "number_of_confirmatory_tests"), 8, "confirmatory test family"),
        (("inference", "overall_support_rule"), "aggregate passes", "overall support rule"),
        (("inference", "sensitivity"), ["median"], "sensitivity set"),
        (("mandatory_safety_diagnostics", "metrics"), ["runtime_millis"], "safety metrics"),
        (("mandatory_safety_diagnostics", "reporting"), "aggregate only", "safety reporting"),
        (("outcome_handling", "legitimate_outcomes_never_excluded"), [], "retained outcome"),
        (("outcome_handling", "allowed_pair_exclusions"), ["bad_seed"], "pair exclusion"),
        (
            ("outcome_handling", "strategy_failure_scoring", "assignment_rate"),
            1.0,
            "failure scoring",
        ),
        (("outcome_handling", "missing_pair_rule"), "impute zero", "missing-pair rule"),
        (("stopping", "desired_result_stopping_allowed"), True, "desired-result stopping"),
        (("stopping", "pilot_stop"), "when stable", "pilot stopping rule"),
        (("stopping", "early_stop_reasons"), [], "early-stop reasons"),
        (("resource_envelope", "external_cost_usd"), 1.0, "external cost"),
        (("lineage", "required"), [], "lineage field set"),
        (("lineage", "large_artifact_boundary"), "repo/results", "artifact boundary"),
        (("lineage", "campaign_execution_prohibited_until"), [], "campaign prerequisite"),
        (("supported_wording",), "Protocol exists.", "supported wording"),
        (("prohibited_wording",), [], "prohibited wording"),
    ),
)
def test_protocol_rejects_scientifically_material_drift(
    tmp_path: Path, path: tuple[object, ...], replacement: object, message: str
) -> None:
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    _set_path(payload, path, replacement)
    mutated = tmp_path / "protocol.json"
    mutated.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(StatisticalRouteBenchProtocolError, match=message):
        load_statistical_routebench_protocol(mutated)


def test_protocol_rejects_unknown_root_fields_and_malformed_files(tmp_path: Path) -> None:
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    payload["post_hoc_override"] = True
    unknown = tmp_path / "unknown.json"
    unknown.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(StatisticalRouteBenchProtocolError, match="protocol fields"):
        load_statistical_routebench_protocol(unknown)

    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    payload["research"]["post_hoc_override"] = True
    nested = tmp_path / "nested.json"
    nested.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(StatisticalRouteBenchProtocolError, match="content identity"):
        load_statistical_routebench_protocol(nested)

    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    with pytest.raises(StatisticalRouteBenchProtocolError, match="valid UTF-8 JSON"):
        load_statistical_routebench_protocol(malformed)
    with pytest.raises(StatisticalRouteBenchProtocolError, match="unreadable"):
        load_statistical_routebench_protocol(tmp_path / "missing.json")


def _set_path(root: object, path: tuple[object, ...], replacement: object) -> None:
    current = root
    for component in path[:-1]:
        current = current[component]  # type: ignore[index]
    current[path[-1]] = replacement  # type: ignore[index]
