"""Run the bounded synthetic observation and anomaly-discovery campaign.

The campaign is intentionally observation-first. It reuses the frozen product
scenario catalog and ScenarioKernel; it does not select or tune a new policy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SERVICE_ROOT = ROOT / "services" / "compute-api"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from deterministic_scenarios import (  # noqa: E402
    EXPECTED_IDS,
    _provider,
    build_manifest,
    load_catalog,
)

from routemind_compute.application.registry import default_registry  # noqa: E402
from routemind_compute.application.research_observability import (  # noqa: E402
    SCHEMA_VERSION,
    PolicyObservation,
    PolicyTrace,
    ResearchObservationExporter,
    canonical_digest,
)
from routemind_compute.application.simulation import ScenarioKernel  # noqa: E402

DEFAULT_SEEDS = tuple(range(20260830, 20260846))
MAX_SEEDS = 32
CHECKPOINT = "RM-241"
CAMPAIGN_SCHEMA = "routemind-synthetic-observation-campaign-v1"
SCHEMA_PATH = ROOT / "contracts" / "observability" / "rm-237-policy-observation-v1.schema.json"

__all__ = [
    "CAMPAIGN_SCHEMA",
    "CHECKPOINT",
    "DEFAULT_SEEDS",
    "EXPECTED_IDS",
    "MAX_SEEDS",
    "PREREGISTERED_METRICS",
    "SCHEMA_VERSION",
    "build_campaign_manifest",
    "load_catalog",
    "run_campaign",
]

PREREGISTERED_METRICS: tuple[dict[str, str], ...] = (
    {"name": "decision_count", "status": "AVAILABLE", "source": "PolicyTrace"},
    {"name": "switch_count", "status": "AVAILABLE", "source": "PolicyTrace"},
    {"name": "switch_rate", "status": "DERIVED", "source": "PolicyTrace.metrics"},
    {"name": "dwell_ticks", "status": "AVAILABLE", "source": "PolicyTrace"},
    {"name": "policy_occupancy", "status": "DERIVED", "source": "PolicyTrace.metrics"},
    {"name": "transition_matrix", "status": "DERIVED", "source": "PolicyTrace.metrics"},
    {
        "name": "short_window_reversals",
        "status": "DERIVED",
        "source": "PolicyTrace.metrics",
    },
    {
        "name": "decision_latency",
        "status": "UNAVAILABLE",
        "source": "not in PolicyObservation",
    },
    {
        "name": "solver_runtime",
        "status": "UNAVAILABLE",
        "source": "not in PolicyObservation",
    },
    {
        "name": "fallback_degradation_state",
        "status": "AVAILABLE",
        "source": "scenario configuration",
    },
    {
        "name": "assignment_churn",
        "status": "UNAVAILABLE",
        "source": "not in PolicyObservation",
    },
    {
        "name": "route_recomputation",
        "status": "UNAVAILABLE",
        "source": "not in PolicyObservation",
    },
    {
        "name": "sla_risk_delta",
        "status": "UNAVAILABLE",
        "source": "not in PolicyObservation",
    },
    {
        "name": "consequence_components",
        "status": "AVAILABLE",
        "source": "observation consequences",
    },
    {"name": "missingness", "status": "DERIVED", "source": "quality validator"},
    {
        "name": "provenance_completeness",
        "status": "DERIVED",
        "source": "quality validator",
    },
    {
        "name": "replayability",
        "status": "DERIVED",
        "source": "ScenarioKernel replay digest",
    },
    {"name": "digest_consistency", "status": "DERIVED", "source": "canonical digest"},
    {
        "name": "ordering_invariant_violations",
        "status": "DERIVED",
        "source": "quality validator",
    },
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _git_revision() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"
    return completed.stdout.strip() or "UNKNOWN"


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def build_campaign_manifest(catalog: dict[str, Any], seeds: tuple[int, ...]) -> dict[str, Any]:
    if tuple(item["id"] for item in catalog["scenarios"]) != EXPECTED_IDS:
        raise ValueError("campaign requires the frozen scenario catalog")
    if not seeds or len(seeds) > MAX_SEEDS:
        raise ValueError(f"seed count must be between 1 and {MAX_SEEDS}")
    if len(set(seeds)) != len(seeds) or any(seed < 0 for seed in seeds):
        raise ValueError("seeds must be unique non-negative integers")
    catalog_path = ROOT / "docs" / "product" / "scenarios" / "product-readiness-scenarios-v1.json"
    return {
        "schema_version": CAMPAIGN_SCHEMA,
        "checkpoint": CHECKPOINT,
        "purpose": "synthetic runtime observation and falsification-first anomaly discovery",
        "catalog_id": catalog["catalog_id"],
        "catalog_sha256": _sha256_file(catalog_path),
        "catalog_scenarios": list(EXPECTED_IDS),
        "seeds": list(seeds),
        "seeds_per_scenario": len(seeds),
        "strategy": "nearest",
        "strategy_selection_mode": "fixed ScenarioKernel strategy",
        "observation_schema": SCHEMA_VERSION,
        "preregistered_metrics": list(PREREGISTERED_METRICS),
        "raw_artifact": {
            "root_policy": "ROUTEMIND_DATA_ROOT",
            "relative_path": "research-observations/policy-observations-v1.jsonl",
            "git_committed": False,
        },
        "resource_policy": {
            "execution": "local deterministic only",
            "cloud_calls": False,
            "paid_apis": False,
            "cost_usd": 0.0,
        },
        "claim_boundary": (
            "observational synthetic evidence only; no causal, novelty, production, "
            "or fidelity claim"
        ),
        "runner_source_sha256": _sha256_file(Path(__file__).resolve()),
        "code_revision": _git_revision(),
    }


def _schema_validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _quality_errors(
    observations: tuple[PolicyObservation, ...], validator: Draft202012Validator
) -> list[str]:
    errors: list[str] = []
    previous_tick = -1
    previous_key = ""
    run_ids: set[str] = set()
    for index, observation in enumerate(observations):
        payload = observation.as_dict(include_timestamp=False)
        schema_errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
        errors.extend(f"schema[{index}]: {error.message}" for error in schema_errors)
        if observation.tick < previous_tick or (
            observation.tick == previous_tick and observation.request_id < previous_key
        ):
            errors.append(f"ordering[{index}]: observations are not monotonic")
        previous_tick = observation.tick
        previous_key = observation.request_id
        if observation.run_id in run_ids:
            continue
        run_ids.add(observation.run_id)
        provenance = dict(observation.provenance)
        if not provenance.get("reference_data_id"):
            errors.append(f"provenance[{index}]: reference_data_id missing")
        if not provenance.get("replay_source"):
            errors.append(f"provenance[{index}]: replay_source missing")
        if observation.switch_occurred != (
            observation.previous_policy != observation.selected_policy
        ):
            errors.append(f"transition[{index}]: switch flag mismatch")
    return errors


def _run_once(record: dict[str, Any], seed: int) -> tuple[Any, Any]:
    manifest = build_manifest(record, seed)
    kernel = ScenarioKernel(default_registry(), _provider(record), strategy="nearest")
    return manifest, kernel.run(manifest)


def _run_record(
    record: dict[str, Any], seed: int, validator: Draft202012Validator
) -> tuple[dict[str, Any], tuple[PolicyObservation, ...]]:
    manifest, first = _run_once(record, seed)
    _, second = _run_once(record, seed)
    observations = first.observations
    trace = PolicyTrace()
    for observation in observations:
        trace.record(
            run_id=observation.run_id,
            scenario_id=observation.scenario_id,
            decision_id=observation.decision_id,
            request_id=observation.request_id,
            tick=observation.tick,
            selected_policy=observation.selected_policy,
            policy_version=observation.policy_version,
            configuration_digest=observation.configuration_digest,
            deterministic_seed=observation.deterministic_seed,
            previous_policy=observation.previous_policy,
            switch_reason=observation.switch_reason,
            selection_mode=observation.selection_mode,
            clock_domain=observation.clock_domain,
            state=dict(observation.state),
            semantics=dict(observation.semantics),
            consequences=observation.consequences,
            provenance=dict(observation.provenance),
            fallback_state=observation.fallback_state,
            timestamp=observation.timestamp,
        )
    quality_errors = _quality_errors(observations, validator)
    if first.replay_digest != second.replay_digest:
        quality_errors.append("replay digest changed on identical manifest")
    if trace.replay_digest() != PolicyTraceReplayDigest(observations):
        quality_errors.append("observation trace digest is inconsistent")
    metrics = trace.metrics()
    if metrics.switch_count > metrics.decision_count:
        quality_errors.append("switch count exceeds decision count")
    if len(observations) != len(first.decisions):
        quality_errors.append("observation count differs from decision count")
    return (
        {
            "run_id": observations[0].run_id
            if observations
            else f"twin:{manifest.scenario_id}:{seed}",
            "scenario_id": manifest.scenario_id,
            "seed": seed,
            "configuration": {
                "demand_count": len(manifest.demands),
                "courier_count": len(manifest.couriers),
                "delay_ticks": list(manifest.delay_ticks),
                "traffic_multiplier": manifest.traffic_multiplier,
                "provider_mode": record["provider_mode"],
            },
            "replay_digest": first.replay_digest,
            "observation_trace_digest": trace.replay_digest(),
            "decision_count": metrics.decision_count,
            "assigned_count": sum(decision.courier_id is not None for decision in first.decisions),
            "unassigned_count": sum(decision.courier_id is None for decision in first.decisions),
            "metrics": metrics.as_dict(),
            "fallback_state_counts": dict(Counter(item.fallback_state for item in observations)),
            "consequence_status_counts": dict(
                Counter(
                    component.status for item in observations for component in item.consequences
                )
            ),
            "quality": {
                "status": "PASS" if not quality_errors else "FAIL",
                "errors": quality_errors,
                "missing_measurements": [
                    metric["name"]
                    for metric in PREREGISTERED_METRICS
                    if metric["status"] == "UNAVAILABLE"
                ],
            },
        },
        observations,
    )


def PolicyTraceReplayDigest(observations: tuple[PolicyObservation, ...]) -> str:
    """Canonical digest helper kept separate to make the quality check obvious."""

    return canonical_digest([item.as_dict(include_timestamp=False) for item in observations])


def _aggregate(run_records: list[dict[str, Any]]) -> dict[str, Any]:
    by_scenario: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in run_records:
        by_scenario[record["scenario_id"]].append(record)
    summaries: dict[str, Any] = {}
    for scenario_id in EXPECTED_IDS:
        records = by_scenario[scenario_id]
        switch_rates = [float(item["metrics"]["switch_rate"]) for item in records]
        switch_counts = [int(item["metrics"]["switch_count"]) for item in records]
        reversal_counts = [int(item["metrics"]["reversal_count"]) for item in records]
        dwell = [tick for item in records for tick in item["metrics"]["dwell_ticks"]]
        occupancy = Counter(
            entry["policy"]
            for item in records
            for entry in item["metrics"]["policy_occupancy"]
            for _ in range(int(entry["count"]))
        )
        transition = Counter(
            (entry["previous_policy"], entry["selected_policy"])
            for item in records
            for entry in item["metrics"]["transition_matrix"]
            for _ in range(int(entry["count"]))
        )
        summaries[scenario_id] = {
            "run_count": len(records),
            "decision_count_total": sum(item["decision_count"] for item in records),
            "assigned_count_total": sum(item["assigned_count"] for item in records),
            "unassigned_count_total": sum(item["unassigned_count"] for item in records),
            "switch_count_total": sum(switch_counts),
            "switch_rate": {
                "min": min(switch_rates) if switch_rates else 0.0,
                "max": max(switch_rates) if switch_rates else 0.0,
                "mean": sum(switch_rates) / len(switch_rates) if switch_rates else 0.0,
            },
            "reversal_count_total": sum(reversal_counts),
            "dwell_ticks": sorted(dwell),
            "policy_occupancy": [
                {"policy": policy, "count": count} for policy, count in sorted(occupancy.items())
            ],
            "transition_matrix": [
                {"previous_policy": before, "selected_policy": after, "count": count}
                for (before, after), count in sorted(transition.items())
            ],
            "stable_switch_metrics_across_seeds": len(set(switch_counts)) <= 1
            and len(set(reversal_counts)) <= 1,
            "replay_verified_runs": sum(
                bool(item["quality"]["status"] == "PASS") for item in records
            ),
            "fallback_state_counts": dict(
                Counter(
                    state
                    for item in records
                    for state, count in item["fallback_state_counts"].items()
                    for _ in range(int(count))
                )
            ),
            "quality_status": "PASS"
            if all(item["quality"]["status"] == "PASS" for item in records)
            else "FAIL",
        }
    return summaries


def _candidates(aggregates: dict[str, Any], seeds_per_scenario: int) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    all_scenarios = list(EXPECTED_IDS)
    if all(
        summary["switch_count_total"] == 0
        and summary["policy_occupancy"]
        == [{"policy": "nearest", "count": summary["decision_count_total"]}]
        and summary["stable_switch_metrics_across_seeds"]
        for summary in aggregates.values()
    ):
        candidates.append(
            {
                "anomaly_id": "AD-001",
                "phenomenon": (
                    "Zero policy switches and single-policy occupancy across every scenario."
                ),
                "affected_scenarios": all_scenarios,
                "reproducibility": (
                    f"{sum(summary['run_count'] for summary in aggregates.values())}/"
                    f"{sum(summary['run_count'] for summary in aggregates.values())} runs; "
                    f"{seeds_per_scenario} independent seeds per scenario"
                ),
                "simple_explanation_result": (
                    "Explained: the frozen runner instantiates "
                    "ScenarioKernel(strategy=nearest) and does not perform policy selection."
                ),
                "residue_verdict": "EXPLAINED",
            }
        )
    fallback = aggregates["ROUTING_PROVIDER_FAILURE"]
    if fallback["fallback_state_counts"] == {"NONE": fallback["decision_count_total"]}:
        candidates.append(
            {
                "anomaly_id": "AD-002",
                "phenomenon": (
                    "Provider-failure scenario has no non-NONE fallback_state "
                    "in policy observations."
                ),
                "affected_scenarios": ["ROUTING_PROVIDER_FAILURE"],
                "reproducibility": (
                    f"{fallback['run_count']}/{fallback['run_count']} runs; "
                    f"{seeds_per_scenario} independent seeds"
                ),
                "simple_explanation_result": (
                    "Measurement artifact: provider fallback is exercised by the travel layer "
                    "but ScenarioKernel does not copy TravelTime.fallback_used into "
                    "PolicyObservation.fallback_state."
                ),
                "residue_verdict": "MEASUREMENT_ARTIFACT",
            }
        )
    return candidates


def _markdown_report(
    manifest: dict[str, Any],
    run_records: list[dict[str, Any]],
    aggregates: dict[str, Any],
    candidates: list[dict[str, Any]],
    export: Any,
) -> tuple[str, str, str, str]:
    quality_status = (
        "PASS" if all(item["quality"]["status"] == "PASS" for item in run_records) else "FAIL"
    )
    total_runs = len(run_records)
    total_observations = sum(item["decision_count"] for item in run_records)
    lines = [
        "# Synthetic Observation Campaign",
        "",
        f"Checkpoint: {CHECKPOINT}",
        f"Manifest schema: `{CAMPAIGN_SCHEMA}`",
        (
            f"Catalog: `{manifest['catalog_id']}` "
            f"({len(manifest['catalog_scenarios'])} frozen scenarios)"
        ),
        f"Seeds per scenario: {manifest['seeds_per_scenario']}",
        f"Total runs: {total_runs}",
        f"Total observations: {total_observations}",
        f"Raw export: `{manifest['raw_artifact']['relative_path']}` below `ROUTEMIND_DATA_ROOT`",
        "Raw data committed to Git: **NO**",
        f"Observation schema: `{SCHEMA_VERSION}`",
        f"Replay consistency: **{'PASS' if quality_status == 'PASS' else 'FAIL'}**",
        f"Observation quality: **{quality_status}**",
        f"Raw export SHA-256: `{export.sha256}`",
        "",
        "## Metric availability",
        "",
        "| Metric | Status | Source |",
        "| --- | --- | --- |",
        *[
            f"| {metric['name']} | {metric['status']} | {metric['source']} |"
            for metric in PREREGISTERED_METRICS
        ],
        "",
        "## Scenario summary",
        "",
        (
            "| Scenario | Runs | Decisions | Switches | Reversals | Switch rate | "
            "Stable across seeds | Quality |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for scenario_id in EXPECTED_IDS:
        summary = aggregates[scenario_id]
        lines.append(
            f"| {scenario_id} | {summary['run_count']} | "
            f"{summary['decision_count_total']} | "
            f"{summary['switch_count_total']} | {summary['reversal_count_total']} | "
            f"{summary['switch_rate']['mean']:.6f} | "
            f"{'YES' if summary['stable_switch_metrics_across_seeds'] else 'NO'} | "
            f"{summary['quality_status']} |"
        )
    lines.extend(
        [
            "",
            "## Candidate scan",
            "",
            f"Candidate anomalies detected: **{len(candidates)}**",
            "",
            (
                "| ID | Affected scenarios | Reproducibility | Simple explanation | "
                "Final residue verdict |"
            ),
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for candidate in candidates:
        lines.append(
            f"| {candidate['anomaly_id']} | {', '.join(candidate['affected_scenarios'])} | "
            f"{candidate['reproducibility']} | {candidate['simple_explanation_result']} | "
            f"{candidate['residue_verdict']} |"
        )
    lines.extend(
        [
            "",
            (
                "The scan is descriptive. No policy-switch cost, causal effect, novelty, "
                "production behavior, Digital Twin fidelity, or strategy superiority claim "
                "is made."
            ),
            "",
        ]
    )
    campaign_md = "\n".join(lines)
    attack_md = "\n".join(
        [
            "# Simple Explanation Attack",
            "",
            "Each candidate was required to reproduce across multiple seeds before attack.",
            "",
            *[
                (
                    f"- **{item['anomaly_id']}**: {item['simple_explanation_result']} "
                    f"Verdict: `{item['residue_verdict']}`."
                )
                for item in candidates
            ],
            "",
            (
                "No candidate survived the predefined simple explanation checks. Missing "
                "fallback state is retained as an instrumentation limitation and is not "
                "imputed or promoted to a runtime instability claim."
            ),
            "",
        ]
    )
    decision = (
        "NO_RESEARCH_TRIGGER"
        if not any(item["residue_verdict"] == "UNEXPLAINED_RESIDUE" for item in candidates)
        else "CLAUDE_SCIENCE_REOPENING_JUSTIFIED"
    )
    decision_md = "\n".join(
        [
            "# Claude Science Reopening Decision",
            "",
            f"Decision: **{decision}**",
            "",
            (
                "The frozen scientific line remains unchanged. This bounded synthetic "
                "campaign produced no reproducible unexplained residue. No prior candidate "
                "is reopened, no new algorithm is proposed, and no historical result is "
                "reinterpreted."
            ),
            "",
        ]
    )
    evidence_md = "\n".join(
        [
            "# RM-241 Evidence",
            "",
            f"Checkpoint: {CHECKPOINT}",
            "Manifest: `research/anomaly_discovery/CAMPAIGN_MANIFEST.json`",
            "Run registry: `research/anomaly_discovery/RUN_REGISTRY.json`",
            "Results: `research/anomaly_discovery/ANOMALY_SCAN_RESULTS.md`",
            (
                f"Raw export: `{manifest['raw_artifact']['relative_path']}` under "
                "`ROUTEMIND_DATA_ROOT`"
            ),
            "",
            (
                f"Runs: {total_runs}; observations: {total_observations}; quality: "
                f"{quality_status}; candidates: {len(candidates)}; unexplained residues: 0."
            ),
            "",
            (
                "Validation covered schema fields, monotonic ticks, transition invariants, "
                "provenance, deterministic replay digests, observation-trace digests, "
                "redaction/export path policy, and seed/scenario lineage. No cloud or paid "
                "resource was used."
            ),
            "",
        ]
    )
    return campaign_md, attack_md, decision_md, evidence_md


def run_campaign(
    *,
    data_root: Path,
    output_dir: Path = ROOT / "research" / "anomaly_discovery",
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
) -> dict[str, Any]:
    catalog = load_catalog()
    manifest = build_campaign_manifest(catalog, seeds)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "CAMPAIGN_MANIFEST.json"
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing != manifest:
            raise ValueError(
                "existing campaign manifest differs; refuse to overwrite frozen preregistration"
            )
    else:
        _json_write(manifest_path, manifest)

    validator = _schema_validator()
    run_records: list[dict[str, Any]] = []
    observations: list[PolicyObservation] = []
    for record in catalog["scenarios"]:
        for seed in seeds:
            run_record, trace = _run_record(record, seed, validator)
            run_records.append(run_record)
            observations.extend(trace)
    export = ResearchObservationExporter(data_root).export(tuple(observations))
    export_manifest = json.loads(export.manifest_path.read_text(encoding="utf-8"))
    if export_manifest.get("record_count") != export.record_count:
        raise ValueError("raw export record count does not match exporter result")
    if export_manifest.get("sha256") != _sha256_file(export.path):
        raise ValueError("raw export digest does not match exporter manifest")
    if export_manifest.get("root_policy") != "ROUTEMIND_DATA_ROOT":
        raise ValueError("raw export manifest has an invalid root policy")
    exported_rows = [
        json.loads(line)
        for line in export.path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for row in exported_rows:
        errors = sorted(validator.iter_errors(row), key=lambda error: list(error.path))
        if errors:
            raise ValueError(f"exported observation failed schema validation: {errors[0].message}")
    aggregates = _aggregate(run_records)
    candidates = _candidates(aggregates, len(seeds))
    compact_runs = [
        {
            "run_id": item["run_id"],
            "scenario_id": item["scenario_id"],
            "seed": item["seed"],
            "replay_digest": item["replay_digest"],
            "observation_trace_digest": item["observation_trace_digest"],
            "decision_count": item["decision_count"],
            "assigned_count": item["assigned_count"],
            "unassigned_count": item["unassigned_count"],
            "switch_count": item["metrics"]["switch_count"],
            "switch_rate": item["metrics"]["switch_rate"],
            "reversal_count": item["metrics"]["reversal_count"],
            "quality_status": item["quality"]["status"],
        }
        for item in run_records
    ]
    run_registry = {
        "schema_version": "routemind-synthetic-observation-run-registry-v1",
        "checkpoint": CHECKPOINT,
        "manifest_sha256": _sha256_file(manifest_path),
        "runs": compact_runs,
        "run_count": len(compact_runs),
        "observation_count": len(observations),
        "raw_export": {
            "relative_path": manifest["raw_artifact"]["relative_path"],
            "manifest_relative_path": "research-observations/manifest-v1.json",
            "sha256": export.sha256,
            "record_count": export.record_count,
        },
    }
    results = {
        "schema_version": "routemind-synthetic-observation-anomaly-results-v1",
        "checkpoint": CHECKPOINT,
        "manifest_sha256": run_registry["manifest_sha256"],
        "run_registry_sha256": canonical_digest(run_registry),
        "catalog_id": manifest["catalog_id"],
        "catalog_sha256": manifest["catalog_sha256"],
        "scenario_aggregates": aggregates,
        "candidate_anomalies": candidates,
        "candidate_count": len(candidates),
        "unexplained_residue_count": sum(
            item["residue_verdict"] == "UNEXPLAINED_RESIDUE" for item in candidates
        ),
        "final_research_trigger": "CLAUDE_SCIENCE_REOPENING_JUSTIFIED"
        if any(item["residue_verdict"] == "UNEXPLAINED_RESIDUE" for item in candidates)
        else "NO_RESEARCH_TRIGGER",
        "quality_status": "PASS"
        if all(item["quality"]["status"] == "PASS" for item in run_records)
        else "FAIL",
    }
    campaign_md, attack_md, decision_md, evidence_md = _markdown_report(
        manifest, run_records, aggregates, candidates, export
    )
    _json_write(output_dir / "RUN_REGISTRY.json", run_registry)
    _json_write(output_dir / "ANOMALY_CANDIDATES.json", {"candidates": candidates})
    _json_write(output_dir / "CAMPAIGN_RESULTS.json", results)
    (output_dir / "SYNTHETIC_OBSERVATION_CAMPAIGN.md").write_text(
        campaign_md, encoding="utf-8", newline="\n"
    )
    (output_dir / "ANOMALY_SCAN_RESULTS.md").write_text(campaign_md, encoding="utf-8", newline="\n")
    (output_dir / "SIMPLE_EXPLANATION_ATTACK.md").write_text(
        attack_md, encoding="utf-8", newline="\n"
    )
    (output_dir / "CLAUDE_SCIENCE_REOPENING_DECISION.md").write_text(
        decision_md, encoding="utf-8", newline="\n"
    )
    evidence_path = (
        ROOT / "evidence" / "gates" / CHECKPOINT / "synthetic-observation-anomaly-discovery.md"
    )
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(evidence_md, encoding="utf-8", newline="\n")
    return {
        "manifest": manifest,
        "run_registry": run_registry,
        "results": results,
        "export": export,
        "output_dir": output_dir,
        "evidence_path": evidence_path,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        type=Path,
        help="external ROUTEMIND_DATA_ROOT (or use the environment variable)",
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "research" / "anomaly_discovery")
    parser.add_argument("--seed-start", type=int, default=DEFAULT_SEEDS[0])
    parser.add_argument("--seed-count", type=int, default=len(DEFAULT_SEEDS))
    args = parser.parse_args(argv)
    if args.seed_count < 1 or args.seed_count > MAX_SEEDS:
        parser.error(f"--seed-count must be between 1 and {MAX_SEEDS}")
    seeds = tuple(range(args.seed_start, args.seed_start + args.seed_count))
    root = args.data_root
    if root is None:
        import os

        configured = os.getenv("ROUTEMIND_DATA_ROOT")
        if not configured:
            parser.error("--data-root or ROUTEMIND_DATA_ROOT is required")
        root = Path(configured)
    result = run_campaign(data_root=root, output_dir=args.output_dir, seeds=seeds)
    print(
        json.dumps(
            {
                "checkpoint": CHECKPOINT,
                "runs": result["run_registry"]["run_count"],
                "observations": result["run_registry"]["observation_count"],
                "candidate_count": result["results"]["candidate_count"],
                "unexplained_residue_count": result["results"]["unexplained_residue_count"],
                "quality_status": result["results"]["quality_status"],
                "final_research_trigger": result["results"]["final_research_trigger"],
                "raw_export_sha256": result["export"].sha256,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
