"""Read-only, lineage-checked reporting for a material R3-325 pilot."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from pathlib import Path
from statistics import fmean, median, stdev
from typing import cast

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.statistical_routebench_protocol import (
    StatisticalRouteBenchProtocol,
    load_statistical_routebench_protocol,
)

_SCHEMA = "routemind-statistical-routebench-artifact-v1"
_REPORT_SCHEMA = "routemind-statistical-routebench-report-v1"
_METRICS = ("scenario_risk_index", "assignment_rate")
_STREAMS = ("demand", "merchant", "courier", "traffic")


class StatisticalRouteBenchReportError(ValueError):
    """Raised when a retained campaign cannot be reported safely."""


@dataclass(frozen=True, slots=True)
class StatisticalRouteBenchReport:
    campaign_id: str
    protocol_id: str
    protocol_sha256: str
    plan_digest: str
    ledger_digest: str
    pilot_analysis_digest: str
    implementation_revision: str
    implementation_ci_run: int
    cells: tuple[dict[str, object], ...]
    multiplicity: dict[str, object]
    diagnostics: dict[str, object]
    claim_boundary: str = "REPORT_FORMATTING_CANNOT_PROMOTE_A_SCIENTIFIC_CLAIM"

    @property
    def report_digest(self) -> str:
        return canonical_digest(self.payload())

    def payload(self) -> dict[str, object]:
        return {
            "report_schema": _REPORT_SCHEMA,
            "campaign_id": self.campaign_id,
            "protocol_id": self.protocol_id,
            "protocol_sha256": self.protocol_sha256,
            "plan_digest": self.plan_digest,
            "ledger_digest": self.ledger_digest,
            "pilot_analysis_digest": self.pilot_analysis_digest,
            "implementation_revision": self.implementation_revision,
            "implementation_ci_run": self.implementation_ci_run,
            "cells": list(self.cells),
            "multiplicity": self.multiplicity,
            "diagnostics": self.diagnostics,
            "claim_boundary": self.claim_boundary,
        }


def build_statistical_routebench_report(
    campaign_directory: Path,
    protocol_path: Path,
) -> StatisticalRouteBenchReport:
    """Validate retained pilot artifacts and build a report without execution."""
    directory = campaign_directory.expanduser().resolve()
    if not directory.is_dir():
        raise StatisticalRouteBenchReportError("campaign directory does not exist")
    source = {
        name: _read_verified(directory / name)
        for name in (
            "campaign-plan.json",
            "execution-environment.json",
            "campaign-ledger.json",
            "pilot-analysis.json",
        )
    }
    _verify_directory_sidecars(directory)
    plan_root = source["campaign-plan.json"]
    ledger_root = source["campaign-ledger.json"]
    analysis_root = source["pilot-analysis.json"]
    environment_root = source["execution-environment.json"]
    _exact_root(
        plan_root, "campaign-plan", {"schema_version", "artifact_kind", "plan_digest", "plan"}
    )
    _exact_root(
        ledger_root,
        "campaign-ledger",
        {"schema_version", "artifact_kind", "plan_digest", "ledger_digest", "ledger"},
    )
    _exact_root(
        analysis_root,
        "pilot-analysis",
        {"schema_version", "artifact_kind", "plan_digest", "analysis_digest", "analysis"},
    )
    _exact_root(
        environment_root,
        "execution-environment",
        {"schema_version", "artifact_kind", "plan_digest", "environment"},
    )
    plan = _mapping(plan_root["plan"], "campaign plan")
    ledger = _mapping(ledger_root["ledger"], "campaign ledger")
    analysis = _mapping(analysis_root["analysis"], "pilot analysis")
    plan_digest = _string(plan_root, "plan_digest")
    ledger_digest = _string(ledger_root, "ledger_digest")
    analysis_digest = _string(analysis_root, "analysis_digest")
    if canonical_digest(plan) != plan_digest or canonical_digest(ledger) != ledger_digest:
        raise StatisticalRouteBenchReportError("campaign plan or ledger digest does not match")
    if canonical_digest(analysis) != analysis_digest:
        raise StatisticalRouteBenchReportError("pilot analysis digest does not match")
    if _string(plan, "phase") != "pilot" or _string(ledger, "phase") != "pilot":
        raise StatisticalRouteBenchReportError("reporter only accepts a pilot campaign")
    protocol = load_statistical_routebench_protocol(protocol_path.expanduser().resolve())
    protocol_id = _string(plan, "protocol_id")
    protocol_sha = _string(plan, "protocol_sha256")
    if protocol_id != protocol.protocol_id or protocol_sha != protocol.manifest_sha256:
        raise StatisticalRouteBenchReportError("campaign protocol lineage does not match manifest")
    if (
        _string(analysis, "protocol_id") != protocol_id
        or _string(analysis, "protocol_sha256") != protocol_sha
    ):
        raise StatisticalRouteBenchReportError("pilot analysis protocol lineage drifted")
    campaign_id = _string(plan, "campaign_id")
    if campaign_id != directory.name:
        raise StatisticalRouteBenchReportError("campaign directory identity drifted")
    environment = _mapping(environment_root["environment"], "execution environment")
    revision = _string(environment, "code_revision")
    ci_run = _integer(environment, "implementation_ci_run")
    records = _list(ledger, "records")
    if len(records) != protocol.pilot_replicates_per_regime * len(protocol.regime_ids):
        raise StatisticalRouteBenchReportError("pilot report does not cover the frozen pair matrix")
    if _integer(ledger, "complete_pair_count") != len(records):
        raise StatisticalRouteBenchReportError("pilot ledger is not complete")
    outcomes = _index_analysis(analysis)
    cells: list[dict[str, object]] = []
    all_attempts: list[dict[str, object]] = []
    seen_pairs: set[tuple[str, int]] = set()
    for regime_id in protocol.regime_ids:
        regime_records = [
            _mapping(record, "pair record")
            for record in records
            if _record_regime(_mapping(record, "pair record")) == regime_id
        ]
        if len(regime_records) != protocol.pilot_replicates_per_regime:
            raise StatisticalRouteBenchReportError("regime pair coverage drifted")
        for record in regime_records:
            pair = _mapping(record["pair_plan"], "pair plan")
            identity = _mapping(_mapping(pair["randomness"], "randomness")["pair"], "pair identity")
            key = (regime_id, _integer(identity, "replicate"))
            if key in seen_pairs:
                raise StatisticalRouteBenchReportError("duplicate pilot pair identity")
            seen_pairs.add(key)
            attempts = [_mapping(item, "arm attempt") for item in _list(record, "attempts")]
            all_attempts.extend(attempts)
            if not _bool(record, "complete"):
                raise StatisticalRouteBenchReportError("incomplete pilot pair cannot be reported")
        for metric_id in _METRICS:
            cell_records = [_mapping(record, "pair record") for record in regime_records]
            values = _paired_values(cell_records, metric_id)
            outcome = outcomes[(regime_id, metric_id)]
            cells.append(
                {
                    "regime_id": regime_id,
                    "metric_id": metric_id,
                    "status": _string(outcome, "status"),
                    "n": len(values["differences"]),
                    "pair_seeds": [_pair_seed(record) for record in cell_records],
                    "distribution": {
                        "candidate": _distribution(values["candidate"]),
                        "comparator": _distribution(values["comparator"]),
                        "paired_difference": _distribution(values["differences"]),
                    },
                    "estimate": outcome.get("estimate"),
                    "power_plan": outcome.get("power_plan"),
                    "failure_code": outcome.get("failure_code"),
                    "failure_detail": outcome.get("failure_detail"),
                    "runtime": _runtime_summary(cell_records),
                    "scenario_manifest_digests": sorted(_scenario_digests(cell_records)),
                    "generator_version": protocol.scenario_design.generator_version,
                    "strategy_versions": {"candidate": "1.0.0", "comparator": "1.0.0"},
                }
            )
    if len(seen_pairs) != len(records):
        raise StatisticalRouteBenchReportError("pilot pair identities are incomplete")
    return StatisticalRouteBenchReport(
        campaign_id=campaign_id,
        protocol_id=protocol_id,
        protocol_sha256=protocol_sha,
        plan_digest=plan_digest,
        ledger_digest=ledger_digest,
        pilot_analysis_digest=analysis_digest,
        implementation_revision=revision,
        implementation_ci_run=ci_run,
        cells=tuple(cells),
        multiplicity=_multiplicity(protocol, outcomes),
        diagnostics=_runtime_summary(all_attempts),
    )


def write_statistical_routebench_report(
    report: StatisticalRouteBenchReport, campaign_directory: Path
) -> Path:
    path = campaign_directory.expanduser().resolve() / "statistical-report.json"
    payload = {
        "schema_version": _SCHEMA,
        "artifact_kind": "statistical-report",
        "report_digest": report.report_digest,
        "report": report.payload(),
    }
    encoded = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode(
        "utf-8"
    )
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if path.exists() and path.read_bytes() != encoded:
        raise StatisticalRouteBenchReportError("statistical report is immutable and differs")
    if not path.exists():
        try:
            with path.open("xb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as error:
            raise StatisticalRouteBenchReportError("unable to write statistical report") from error
    digest = sha256(encoded).hexdigest() + "\n"
    if sidecar.exists() and sidecar.read_text(encoding="ascii") != digest:
        raise StatisticalRouteBenchReportError(
            "statistical report sidecar is immutable and differs"
        )
    if not sidecar.exists():
        sidecar.write_text(digest, encoding="ascii")
    return path


def _read_verified(path: Path) -> dict[str, object]:
    try:
        raw = path.read_bytes()
        expected = path.with_suffix(path.suffix + ".sha256").read_text(encoding="ascii").strip()
        value = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise StatisticalRouteBenchReportError(f"unreadable report source: {path.name}") from error
    if sha256(raw).hexdigest() != expected:
        raise StatisticalRouteBenchReportError(f"report source checksum mismatch: {path.name}")
    return _mapping(value, "report source")


def _verify_directory_sidecars(directory: Path) -> None:
    for path in directory.rglob("*"):
        if path.is_file() and not path.name.endswith(".sha256"):
            sidecar = path.with_suffix(path.suffix + ".sha256")
            if (
                not sidecar.is_file()
                or sha256(path.read_bytes()).hexdigest()
                != sidecar.read_text(encoding="ascii").strip()
            ):
                raise StatisticalRouteBenchReportError(
                    f"artifact sidecar missing or invalid: {path.name}"
                )


def _exact_root(value: dict[str, object], kind: str, keys: set[str]) -> None:
    if (
        set(value) != keys
        or value.get("schema_version") != _SCHEMA
        or value.get("artifact_kind") != kind
    ):
        raise StatisticalRouteBenchReportError(f"{kind} artifact shape drifted")


def _index_analysis(analysis: dict[str, object]) -> dict[tuple[str, str], dict[str, object]]:
    outcomes = _list(analysis, "outcomes")
    indexed: dict[tuple[str, str], dict[str, object]] = {}
    for item in outcomes:
        outcome = _mapping(item, "analysis outcome")
        key = (_string(outcome, "regime_id"), _string(outcome, "metric_id"))
        if key in indexed:
            raise StatisticalRouteBenchReportError("analysis contains duplicate metric identity")
        indexed[key] = outcome
    if len(indexed) != 16:
        raise StatisticalRouteBenchReportError("analysis does not retain the frozen 16-test family")
    return indexed


def _record_regime(record: dict[str, object]) -> str:
    pair = _mapping(record["pair_plan"], "pair plan")
    randomness = _mapping(pair["randomness"], "randomness")
    identity = _mapping(randomness["pair"], "pair identity")
    return _string(identity, "regime_id")


def _paired_values(records: list[dict[str, object]], metric: str) -> dict[str, list[float]]:
    candidate: list[float] = []
    comparator: list[float] = []
    for record in records:
        attempts = [_mapping(item, "arm attempt") for item in _list(record, "attempts")]
        terminal = {_string(item, "arm_role"): item for item in attempts}
        if set(terminal) != {"candidate", "comparator"}:
            raise StatisticalRouteBenchReportError("pair does not contain two terminal arms")
        field = "scenario_risk_index" if metric == "scenario_risk_index" else "assignment_rate"
        candidate.append(_number(terminal["candidate"], field))
        comparator.append(_number(terminal["comparator"], field))
    return {
        "candidate": candidate,
        "comparator": comparator,
        "differences": [a - b for a, b in zip(candidate, comparator, strict=True)],
    }


def _pair_seed(record: dict[str, object]) -> dict[str, object]:
    pair = _mapping(record["pair_plan"], "pair plan")
    randomness = _mapping(pair["randomness"], "randomness")
    identity = _mapping(randomness["pair"], "pair identity")
    streams = _list(randomness, "streams")
    if tuple(_string(_mapping(item, "stream"), "stream_name") for item in streams) != _STREAMS:
        raise StatisticalRouteBenchReportError("pair stream order drifted")
    return {
        "phase": _string(identity, "phase"),
        "regime_id": _string(identity, "regime_id"),
        "replicate": _integer(identity, "replicate"),
        "streams": streams,
        "pair_plan_digest": canonical_digest(randomness),
    }


def _runtime_summary(records: list[dict[str, object]]) -> dict[str, object]:
    attempts = (
        records
        if not records or "attempts" not in records[0]
        else [item for record in records for item in _list(record, "attempts")]
    )
    mapped = [_mapping(item, "arm attempt") for item in attempts]
    runtimes = [_number(item, "runtime_millis") for item in mapped]
    outcomes: dict[str, int] = {}
    strategies: dict[str, dict[str, object]] = {}
    for item in mapped:
        outcome = _string(item, "outcome")
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
        strategy = _string(item, "strategy")
        summary = strategies.setdefault(
            strategy,
            {
                "arm_count": 0,
                "runtime_millis": [],
                "strategy_failure_count": 0,
                "fallback_count": 0,
                "timeout_count": 0,
            },
        )
        summary["arm_count"] = cast(int, summary["arm_count"]) + 1
        cast(list[float], summary["runtime_millis"]).append(_number(item, "runtime_millis"))
        for field in ("strategy_failure_count", "fallback_count", "timeout_count"):
            summary[field] = cast(int, summary[field]) + _integer(item, field)
    for summary in strategies.values():
        values = cast(list[float], summary.pop("runtime_millis"))
        summary.update(_distribution(values))
    return {
        "arm_count": len(mapped),
        "outcome_counts": dict(sorted(outcomes.items())),
        "failure_count": sum(_integer(item, "strategy_failure_count") for item in mapped),
        "fallback_count": sum(_integer(item, "fallback_count") for item in mapped),
        "timeout_count": sum(_integer(item, "timeout_count") for item in mapped),
        "runtime_millis": _distribution(runtimes) if runtimes else _distribution([0.0]),
        "by_strategy": strategies,
    }


def _scenario_digests(records: list[dict[str, object]]) -> set[str]:
    return {
        _string(_mapping(item, "arm attempt"), "scenario_manifest_digest")
        for record in records
        for item in _list(record, "attempts")
    }


def _multiplicity(
    protocol: StatisticalRouteBenchProtocol, outcomes: dict[tuple[str, str], dict[str, object]]
) -> dict[str, object]:
    tests = []
    for metric in _METRICS:
        for regime in protocol.regime_ids:
            outcome = outcomes[(regime, metric)]
            status = _string(outcome, "status")
            tests.append(
                {
                    "regime_id": regime,
                    "metric_id": metric,
                    "raw_p_value": None,
                    "adjusted_p_value": None,
                    "rejected": False,
                    "disposition": "NOT_EXECUTED_NON_ESTIMABLE_PILOT"
                    if status != "PLANNED"
                    else "NOT_EXECUTED_NO_CONFIRMATORY_CAMPAIGN",
                }
            )
    return {
        "method": protocol.multiplicity_method,
        "family": protocol.multiplicity_family,
        "familywise_alpha": protocol.familywise_alpha,
        "family_size": 16,
        "tests": tests,
        "disposition": "CONFIRMATORY_NOT_EXECUTED",
        "claim_boundary": "NO_MULTIPLICITY_RESULT_OR_STRATEGY_CLAIM_FROM_PILOT_REPORT",
    }


def _distribution(values: list[float]) -> dict[str, object]:
    if not values or any(not isfinite(value) for value in values):
        raise StatisticalRouteBenchReportError("distribution contains no finite values")
    ordered = sorted(values)
    return {
        "n": len(values),
        "values": list(values),
        "minimum": ordered[0],
        "p05": _quantile(ordered, 0.05),
        "p25": _quantile(ordered, 0.25),
        "median": median(ordered),
        "mean": fmean(values),
        "p75": _quantile(ordered, 0.75),
        "p95": _quantile(ordered, 0.95),
        "maximum": ordered[-1],
        "sample_standard_deviation": stdev(values) if len(values) > 1 else 0.0,
    }


def _quantile(values: list[float], probability: float) -> float:
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise StatisticalRouteBenchReportError(f"{label} must be an object")
    return value


def _list(value: dict[str, object], key: str) -> list[object]:
    item = value.get(key)
    if not isinstance(item, list):
        raise StatisticalRouteBenchReportError(f"{key} must be an array")
    return item


def _string(value: dict[str, object], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise StatisticalRouteBenchReportError(f"{key} must be a non-blank string")
    return item


def _integer(value: dict[str, object], key: str) -> int:
    item = value.get(key)
    if not isinstance(item, int) or isinstance(item, bool):
        raise StatisticalRouteBenchReportError(f"{key} must be an integer")
    return item


def _number(value: dict[str, object], key: str) -> float:
    item = value.get(key)
    if not isinstance(item, (int, float)) or isinstance(item, bool) or not isfinite(float(item)):
        raise StatisticalRouteBenchReportError(f"{key} must be a finite number")
    return float(item)


def _bool(value: dict[str, object], key: str) -> bool:
    item = value.get(key)
    if not isinstance(item, bool):
        raise StatisticalRouteBenchReportError(f"{key} must be boolean")
    return item


__all__ = [
    "StatisticalRouteBenchReport",
    "StatisticalRouteBenchReportError",
    "build_statistical_routebench_report",
    "write_statistical_routebench_report",
]
