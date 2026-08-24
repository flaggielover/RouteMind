"""Immutable, resumable external artifacts for Statistical RouteBench campaigns."""

from __future__ import annotations

import json
import os
import platform
import re
import sys
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import cast

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.statistical_routebench_analysis import (
    PilotCampaignAnalysis,
)
from routemind_compute.application.statistical_routebench_campaign import (
    ArmExecutionAttempt,
    ArmExecutor,
    ArmOutcome,
    ArmRole,
    PairExecutionRecord,
    PilotPairExecutionPlan,
    StatisticalRouteBenchCampaignLedger,
    StatisticalRouteBenchCampaignPlan,
    execute_campaign_pair,
    summarize_campaign_records,
)

_SCHEMA = "routemind-statistical-routebench-artifact-v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class StatisticalRouteBenchArtifactError(ValueError):
    """Raised when external campaign artifacts are unsafe or inconsistent."""


@dataclass(frozen=True, slots=True)
class CampaignExecutionEnvironment:
    code_revision: str
    implementation_ci_run: int
    python_version: str
    platform_system: str
    platform_release: str
    machine: str
    processor: str
    threads_per_arm: int

    @classmethod
    def capture(cls, plan: StatisticalRouteBenchCampaignPlan) -> CampaignExecutionEnvironment:
        return cls(
            code_revision=plan.authorization.implementation_revision,
            implementation_ci_run=plan.authorization.implementation_ci_run,
            python_version=platform.python_version(),
            platform_system=platform.system(),
            platform_release=platform.release(),
            machine=platform.machine(),
            processor=platform.processor(),
            threads_per_arm=plan.resource_estimate.threads_per_arm,
        )

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[0-9a-f]{40}", self.code_revision):
            raise StatisticalRouteBenchArtifactError("environment code revision is invalid")
        if (
            not isinstance(self.implementation_ci_run, int)
            or isinstance(self.implementation_ci_run, bool)
            or self.implementation_ci_run <= 0
            or self.threads_per_arm != 1
        ):
            raise StatisticalRouteBenchArtifactError("environment execution identity is invalid")
        if any(
            not value.strip()
            for value in (
                self.python_version,
                self.platform_system,
                self.platform_release,
                self.machine,
            )
        ):
            raise StatisticalRouteBenchArtifactError("environment fields must not be blank")

    def payload(self) -> dict[str, object]:
        return {
            "code_revision": self.code_revision,
            "implementation_ci_run": self.implementation_ci_run,
            "python_version": self.python_version,
            "platform_system": self.platform_system,
            "platform_release": self.platform_release,
            "machine": self.machine,
            "processor": self.processor,
            "threads_per_arm": self.threads_per_arm,
            "python_executable_name": Path(sys.executable).name,
        }


@dataclass(frozen=True, slots=True)
class CampaignArtifactResult:
    output_directory: Path
    campaign_plan_path: Path
    environment_path: Path
    ledger_path: Path
    artifact_bytes: int
    ledger: StatisticalRouteBenchCampaignLedger


class CampaignArtifactStore:
    """Content-addressed write-once store rooted below ROUTEMIND_DATA_ROOT."""

    def __init__(
        self,
        data_root: Path,
        plan: StatisticalRouteBenchCampaignPlan,
        environment: CampaignExecutionEnvironment,
    ) -> None:
        root = data_root.expanduser().resolve()
        if not root.is_dir():
            raise StatisticalRouteBenchArtifactError("ROUTEMIND_DATA_ROOT must exist")
        if (
            environment.code_revision != plan.authorization.implementation_revision
            or environment.implementation_ci_run != plan.authorization.implementation_ci_run
            or environment.threads_per_arm != plan.resource_estimate.threads_per_arm
        ):
            raise StatisticalRouteBenchArtifactError("environment escaped campaign authorization")
        allowed = (root / plan.artifact_relative_root).resolve()
        output = (allowed / plan.campaign_id).resolve()
        try:
            output.relative_to(allowed)
        except ValueError as error:
            raise StatisticalRouteBenchArtifactError(
                "campaign output escaped its data root"
            ) from error
        if output == allowed:
            raise StatisticalRouteBenchArtifactError(
                "campaign requires a distinct output directory"
            )
        self.plan = plan
        self.environment = environment
        self.output_directory = output
        self.pair_directory = output / "pairs"
        self.maximum_bytes = plan.resource_estimate.maximum_external_artifact_mebibytes * 1024**2

    def initialize(self) -> tuple[Path, Path]:
        self.pair_directory.mkdir(parents=True, exist_ok=True)
        plan_path = self.output_directory / "campaign-plan.json"
        environment_path = self.output_directory / "execution-environment.json"
        _write_or_verify_json(
            plan_path,
            {
                "schema_version": _SCHEMA,
                "artifact_kind": "campaign-plan",
                "plan_digest": self.plan.plan_digest,
                "plan": self.plan.payload(),
            },
        )
        _write_or_verify_json(
            environment_path,
            {
                "schema_version": _SCHEMA,
                "artifact_kind": "execution-environment",
                "plan_digest": self.plan.plan_digest,
                "environment": self.environment.payload(),
            },
        )
        self.enforce_size_limit()
        return plan_path, environment_path

    def pair_path(self, pair: PilotPairExecutionPlan) -> Path:
        identity = pair.randomness.pair
        return self.pair_directory / f"{identity.regime_id}-{identity.replicate:04d}.json"

    def write_record(self, record: PairExecutionRecord) -> Path:
        if record.pair_plan not in self.plan.pairs:
            raise StatisticalRouteBenchArtifactError("pair record is not part of the campaign plan")
        path = self.pair_path(record.pair_plan)
        _write_or_verify_json(
            path,
            {
                "schema_version": _SCHEMA,
                "artifact_kind": "pair-record",
                "plan_digest": self.plan.plan_digest,
                "record_digest": record.record_digest,
                "record": record.payload(),
            },
        )
        self.enforce_size_limit()
        return path

    def load_record(self, pair: PilotPairExecutionPlan) -> PairExecutionRecord | None:
        path = self.pair_path(pair)
        if not path.exists():
            return None
        root = _read_verified_json(path)
        _exact_keys(
            root,
            {"schema_version", "artifact_kind", "plan_digest", "record_digest", "record"},
            "pair artifact",
        )
        if (
            _string(root, "schema_version") != _SCHEMA
            or _string(root, "artifact_kind") != "pair-record"
            or _string(root, "plan_digest") != self.plan.plan_digest
        ):
            raise StatisticalRouteBenchArtifactError("pair artifact campaign identity drifted")
        record_value = _mapping(root.get("record"), "pair record")
        pair_plan_value = record_value.get("pair_plan")
        if canonical_digest(pair_plan_value) != pair.pair_plan_digest:
            raise StatisticalRouteBenchArtifactError("pair artifact plan identity drifted")
        attempts_value = record_value.get("attempts")
        if not isinstance(attempts_value, list):
            raise StatisticalRouteBenchArtifactError("pair artifact attempts are invalid")
        attempts = tuple(_parse_attempt(item) for item in attempts_value)
        record = PairExecutionRecord(pair, attempts)
        if (
            record_value.get("complete") is not record.complete
            or _string(root, "record_digest") != record.record_digest
        ):
            raise StatisticalRouteBenchArtifactError("pair artifact digest or status drifted")
        return record

    def write_ledger(self, ledger: StatisticalRouteBenchCampaignLedger) -> Path:
        if ledger.plan_digest != self.plan.plan_digest:
            raise StatisticalRouteBenchArtifactError("ledger escaped its campaign plan")
        path = self.output_directory / "campaign-ledger.json"
        _write_or_verify_json(
            path,
            {
                "schema_version": _SCHEMA,
                "artifact_kind": "campaign-ledger",
                "plan_digest": self.plan.plan_digest,
                "ledger_digest": ledger.ledger_digest,
                "ledger": ledger.payload(),
            },
        )
        self.enforce_size_limit()
        return path

    def write_pilot_analysis(self, analysis: PilotCampaignAnalysis) -> Path:
        if (
            self.plan.phase != "pilot"
            or analysis.campaign_plan_digest != self.plan.plan_digest
            or analysis.protocol_id != self.plan.protocol_id
            or analysis.protocol_sha256 != self.plan.protocol_sha256
        ):
            raise StatisticalRouteBenchArtifactError("pilot analysis escaped its campaign plan")
        path = self.output_directory / "pilot-analysis.json"
        _write_or_verify_json(
            path,
            {
                "schema_version": _SCHEMA,
                "artifact_kind": "pilot-analysis",
                "plan_digest": self.plan.plan_digest,
                "analysis_digest": analysis.analysis_digest,
                "analysis": analysis.payload(),
            },
        )
        self.enforce_size_limit()
        return path

    def enforce_size_limit(self) -> int:
        size = sum(
            path.stat().st_size for path in self.output_directory.rglob("*") if path.is_file()
        )
        if size > self.maximum_bytes:
            raise StatisticalRouteBenchArtifactError("campaign artifact envelope was exceeded")
        return size


def run_campaign_to_artifacts(
    plan: StatisticalRouteBenchCampaignPlan,
    executor: ArmExecutor,
    data_root: Path,
) -> CampaignArtifactResult:
    environment = CampaignExecutionEnvironment.capture(plan)
    store = CampaignArtifactStore(data_root, plan, environment)
    plan_path, environment_path = store.initialize()
    records: list[PairExecutionRecord] = []
    for pair in plan.pairs:
        record = store.load_record(pair)
        if record is None:
            record = execute_campaign_pair(pair, executor)
            store.write_record(record)
        records.append(record)
    ledger = summarize_campaign_records(plan, tuple(records))
    ledger_path = store.write_ledger(ledger)
    return CampaignArtifactResult(
        output_directory=store.output_directory,
        campaign_plan_path=plan_path,
        environment_path=environment_path,
        ledger_path=ledger_path,
        artifact_bytes=store.enforce_size_limit(),
        ledger=ledger,
    )


def write_pilot_analysis_artifact(
    plan: StatisticalRouteBenchCampaignPlan,
    analysis: PilotCampaignAnalysis,
    data_root: Path,
) -> Path:
    environment = CampaignExecutionEnvironment.capture(plan)
    store = CampaignArtifactStore(data_root, plan, environment)
    store.initialize()
    return store.write_pilot_analysis(analysis)


def _parse_attempt(value: object) -> ArmExecutionAttempt:
    item = _mapping(value, "arm attempt")
    expected = {
        "pair_plan_digest",
        "arm_role",
        "strategy",
        "strategy_version",
        "attempt",
        "outcome",
        "started_at_utc",
        "completed_at_utc",
        "request_count",
        "assigned_count",
        "scenario_risk_index",
        "assignment_rate",
        "runtime_millis",
        "strategy_failure_count",
        "fallback_count",
        "timeout_count",
        "event_ids",
        "scenario_manifest_digest",
        "stream_realization_digests",
        "deterministic_result_digest",
        "failure_code",
    }
    _exact_keys(item, expected, "arm attempt")
    role = _string(item, "arm_role")
    outcome = _string(item, "outcome")
    if role not in {"candidate", "comparator"} or outcome not in {
        "COMPLETED",
        "TIMEOUT",
        "STRATEGY_FAILURE",
        "FALLBACK",
        "HARNESS_DEFECT",
        "INFRASTRUCTURE_DEFECT",
    }:
        raise StatisticalRouteBenchArtifactError("arm attempt role or outcome is invalid")
    return ArmExecutionAttempt(
        pair_plan_digest=_string(item, "pair_plan_digest"),
        arm_role=cast(ArmRole, role),
        strategy=_string(item, "strategy"),
        strategy_version=_string(item, "strategy_version"),
        attempt=_integer(item, "attempt"),
        outcome=cast(ArmOutcome, outcome),
        started_at_utc=_string(item, "started_at_utc"),
        completed_at_utc=_string(item, "completed_at_utc"),
        request_count=_optional_integer(item, "request_count"),
        assigned_count=_optional_integer(item, "assigned_count"),
        scenario_risk_index=_optional_number(item, "scenario_risk_index"),
        assignment_rate=_optional_number(item, "assignment_rate"),
        runtime_millis=_number(item, "runtime_millis"),
        strategy_failure_count=_integer(item, "strategy_failure_count"),
        fallback_count=_integer(item, "fallback_count"),
        timeout_count=_integer(item, "timeout_count"),
        event_ids=_string_tuple(item.get("event_ids"), "event ids"),
        scenario_manifest_digest=_optional_string(item, "scenario_manifest_digest"),
        stream_realization_digests=_digest_pairs(
            item.get("stream_realization_digests"), "stream realization digests"
        ),
        deterministic_result_digest=_string(item, "deterministic_result_digest"),
        failure_code=_optional_string(item, "failure_code"),
    )


def _write_or_verify_json(path: Path, payload: dict[str, object]) -> None:
    encoded = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode(
        "utf-8"
    )
    digest = sha256(encoded).hexdigest()
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if path.exists():
        if path.read_bytes() != encoded:
            raise StatisticalRouteBenchArtifactError(
                f"immutable campaign artifact already differs: {path.name}"
            )
    else:
        try:
            with path.open("xb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as error:
            raise StatisticalRouteBenchArtifactError(
                f"unable to write campaign artifact: {path.name}"
            ) from error
    sidecar_payload = (digest + "\n").encode("ascii")
    if sidecar.exists():
        if sidecar.read_bytes() != sidecar_payload:
            raise StatisticalRouteBenchArtifactError(
                f"campaign artifact sidecar differs: {path.name}"
            )
    else:
        try:
            with sidecar.open("xb") as stream:
                stream.write(sidecar_payload)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as error:
            raise StatisticalRouteBenchArtifactError(
                f"unable to write campaign checksum: {path.name}"
            ) from error


def _read_verified_json(path: Path) -> dict[str, object]:
    try:
        raw = path.read_bytes()
        expected = path.with_suffix(path.suffix + ".sha256").read_text(encoding="ascii").strip()
        value = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise StatisticalRouteBenchArtifactError(
            f"campaign artifact is unreadable: {path.name}"
        ) from error
    if not _SHA256.fullmatch(expected) or sha256(raw).hexdigest() != expected:
        raise StatisticalRouteBenchArtifactError(
            f"campaign artifact checksum mismatch: {path.name}"
        )
    return dict(_mapping(value, "campaign artifact"))


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise StatisticalRouteBenchArtifactError(f"{label} must be an object")
    return value


def _exact_keys(value: dict[str, object], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise StatisticalRouteBenchArtifactError(f"{label} fields drifted")


def _string(value: dict[str, object], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise StatisticalRouteBenchArtifactError(f"{key} must be a non-blank string")
    return item


def _optional_string(value: dict[str, object], key: str) -> str | None:
    item = value.get(key)
    if item is None:
        return None
    if not isinstance(item, str) or not item.strip():
        raise StatisticalRouteBenchArtifactError(f"{key} must be null or non-blank")
    return item


def _integer(value: dict[str, object], key: str) -> int:
    item = value.get(key)
    if not isinstance(item, int) or isinstance(item, bool):
        raise StatisticalRouteBenchArtifactError(f"{key} must be an integer")
    return item


def _optional_integer(value: dict[str, object], key: str) -> int | None:
    item = value.get(key)
    if item is None:
        return None
    return _integer(value, key)


def _number(value: dict[str, object], key: str) -> float:
    item = value.get(key)
    if not isinstance(item, (int, float)) or isinstance(item, bool):
        raise StatisticalRouteBenchArtifactError(f"{key} must be numeric")
    return float(item)


def _optional_number(value: dict[str, object], key: str) -> float | None:
    item = value.get(key)
    if item is None:
        return None
    return _number(value, key)


def _string_tuple(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise StatisticalRouteBenchArtifactError(f"{label} must be a string array")
    return tuple(value)


def _digest_pairs(value: object, label: str) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, list):
        raise StatisticalRouteBenchArtifactError(f"{label} must be an array")
    result: list[tuple[str, str]] = []
    for item in value:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not all(isinstance(component, str) for component in item)
        ):
            raise StatisticalRouteBenchArtifactError(f"{label} entries are invalid")
        result.append((item[0], item[1]))
    return tuple(result)


__all__ = [
    "CampaignArtifactResult",
    "CampaignArtifactStore",
    "CampaignExecutionEnvironment",
    "StatisticalRouteBenchArtifactError",
    "run_campaign_to_artifacts",
    "write_pilot_analysis_artifact",
]
