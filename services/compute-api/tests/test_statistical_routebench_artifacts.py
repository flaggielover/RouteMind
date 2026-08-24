from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from routemind_compute.application import statistical_routebench_artifacts as artifacts
from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.statistical_routebench_analysis import (
    analyze_pilot_campaign,
)
from routemind_compute.application.statistical_routebench_artifacts import (
    CampaignArtifactStore,
    CampaignExecutionEnvironment,
    StatisticalRouteBenchArtifactError,
    run_campaign_to_artifacts,
    write_pilot_analysis_artifact,
)
from routemind_compute.application.statistical_routebench_campaign import (
    ArmExecutionAttempt,
    ArmRole,
    CampaignAuthorization,
    PilotPairExecutionPlan,
    StatisticalRouteBenchCampaignPlan,
    build_pilot_campaign_plan,
    execute_campaign,
    execute_campaign_pair,
)
from routemind_compute.application.statistical_routebench_protocol import (
    load_statistical_routebench_protocol,
)

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = (
    ROOT
    / "docs"
    / "research"
    / "r3"
    / "manifests"
    / "statistical-routebench"
    / "statistical-routebench-v1.json"
)
STREAMS = tuple(
    (name, canonical_digest(name)) for name in ("demand", "merchant", "courier", "traffic")
)


def plan(
    campaign_id: str = "synthetic-artifact-campaign",
    protocol_id: str = "synthetic-artifact-validation",
) -> StatisticalRouteBenchCampaignPlan:
    protocol = replace(
        load_statistical_routebench_protocol(PROTOCOL_PATH),
        protocol_id=protocol_id,
    )
    return build_pilot_campaign_plan(
        protocol,
        campaign_id,
        CampaignAuthorization("1" * 40, 123456, "success", "2026-08-24T12:00:00Z"),
    )


def completed_attempt(
    pair: PilotPairExecutionPlan, role: ArmRole, number: int
) -> ArmExecutionAttempt:
    strategy = pair.candidate_strategy if role == "candidate" else pair.comparator_strategy
    return ArmExecutionAttempt(
        pair_plan_digest=pair.pair_plan_digest,
        arm_role=role,
        strategy=strategy,
        strategy_version="1.0.0",
        attempt=number,
        outcome="COMPLETED",
        started_at_utc="2026-08-24T12:00:00.000Z",
        completed_at_utc="2026-08-24T12:00:00.001Z",
        request_count=2,
        assigned_count=1,
        scenario_risk_index=0.5,
        assignment_rate=0.5,
        runtime_millis=1.0,
        strategy_failure_count=0,
        fallback_count=0,
        timeout_count=0,
        event_ids=("event-1", "event-2"),
        scenario_manifest_digest="a" * 64,
        stream_realization_digests=STREAMS,
        deterministic_result_digest=canonical_digest([pair.pair_plan_digest, role, number]),
    )


def store_with_record(
    tmp_path: Path,
) -> tuple[CampaignArtifactStore, PilotPairExecutionPlan, Path]:
    campaign = plan()
    store = CampaignArtifactStore(
        tmp_path, campaign, CampaignExecutionEnvironment.capture(campaign)
    )
    store.initialize()
    pair = campaign.pairs[0]
    record = execute_campaign_pair(pair, completed_attempt)
    return store, pair, store.write_record(record)


Mutation = Callable[[dict[str, Any]], None]


def rewrite_json(path: Path, mutate: Mutation) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)
    encoded = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    path.write_bytes(encoded)
    path.with_suffix(path.suffix + ".sha256").write_text(
        sha256(encoded).hexdigest() + "\n", encoding="ascii"
    )


def test_campaign_artifacts_are_write_once_content_addressed_and_resumable(
    tmp_path: Path,
) -> None:
    campaign = plan()
    calls: list[tuple[str, int, str, int]] = []

    def executor(pair: PilotPairExecutionPlan, role: ArmRole, number: int) -> ArmExecutionAttempt:
        identity = pair.randomness.pair
        calls.append((identity.regime_id, identity.replicate, role, number))
        return completed_attempt(pair, role, number)

    first = run_campaign_to_artifacts(campaign, executor, tmp_path)

    assert first.ledger.complete_pair_count == 64
    assert first.ledger.retained_attempt_count == 128
    assert len(calls) == 128
    assert len(tuple((first.output_directory / "pairs").glob("*.json"))) == 64
    assert len(tuple(first.output_directory.rglob("*.sha256"))) == 67
    assert first.campaign_plan_path.is_file()
    assert first.environment_path.is_file()
    assert first.ledger_path.is_file()
    initial_bytes = first.artifact_bytes

    second = run_campaign_to_artifacts(campaign, executor, tmp_path)

    assert len(calls) == 128
    assert second.ledger.ledger_digest == first.ledger.ledger_digest
    assert second.artifact_bytes == initial_bytes


def test_resume_rejects_corrupt_pair_instead_of_rerunning_or_overwriting(
    tmp_path: Path,
) -> None:
    campaign = plan()
    result = run_campaign_to_artifacts(campaign, completed_attempt, tmp_path)
    pair_path = next((result.output_directory / "pairs").glob("*.json"))
    pair_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(StatisticalRouteBenchArtifactError, match="checksum mismatch"):
        run_campaign_to_artifacts(campaign, completed_attempt, tmp_path)


def test_existing_campaign_id_rejects_changed_plan(tmp_path: Path) -> None:
    campaign = plan()
    environment = CampaignExecutionEnvironment.capture(campaign)
    CampaignArtifactStore(tmp_path, campaign, environment).initialize()
    changed = replace(
        campaign,
        authorization=replace(campaign.authorization, authorized_at_utc="2026-08-24T12:00:01Z"),
    )

    with pytest.raises(StatisticalRouteBenchArtifactError, match="already differs"):
        CampaignArtifactStore(
            tmp_path, changed, CampaignExecutionEnvironment.capture(changed)
        ).initialize()


def test_artifact_store_requires_existing_root_and_matching_environment(tmp_path: Path) -> None:
    campaign = plan()
    environment = CampaignExecutionEnvironment.capture(campaign)
    with pytest.raises(StatisticalRouteBenchArtifactError, match="must exist"):
        CampaignArtifactStore(tmp_path / "missing", campaign, environment)
    with pytest.raises(StatisticalRouteBenchArtifactError, match="authorization"):
        CampaignArtifactStore(
            tmp_path,
            campaign,
            replace(environment, code_revision="2" * 40),
        )
    with pytest.raises(StatisticalRouteBenchArtifactError, match="environment fields"):
        replace(environment, machine="")
    with pytest.raises(StatisticalRouteBenchArtifactError, match="code revision"):
        replace(environment, code_revision="short")
    with pytest.raises(StatisticalRouteBenchArtifactError, match="execution identity"):
        replace(environment, implementation_ci_run=0)


def test_artifact_size_envelope_is_enforced(tmp_path: Path) -> None:
    campaign = plan()
    constrained = replace(
        campaign,
        resource_estimate=replace(
            campaign.resource_estimate, maximum_external_artifact_mebibytes=1
        ),
    )
    store = CampaignArtifactStore(
        tmp_path, constrained, CampaignExecutionEnvironment.capture(constrained)
    )
    store.initialize()
    (store.output_directory / "oversized.bin").write_bytes(b"x" * (1024**2))

    with pytest.raises(StatisticalRouteBenchArtifactError, match="envelope"):
        store.enforce_size_limit()


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        (lambda root: root.update(plan_digest="b" * 64), "campaign identity"),
        (lambda root: root["record"].update(pair_plan={}), "plan identity"),
        (lambda root: root["record"].update(attempts={}), "attempts are invalid"),
        (lambda root: root.update(record_digest="b" * 64), "digest or status"),
        (lambda root: root["record"].update(complete=False), "digest or status"),
    ),
)
def test_record_resume_parser_rejects_verified_but_semantically_drifted_payload(
    tmp_path: Path, mutation: Mutation, message: str
) -> None:
    store, pair, path = store_with_record(tmp_path)
    rewrite_json(path, mutation)
    with pytest.raises(StatisticalRouteBenchArtifactError, match=message):
        store.load_record(pair)


def test_store_rejects_outsider_record_and_wrong_ledger(tmp_path: Path) -> None:
    store, _, _ = store_with_record(tmp_path)
    other = plan("synthetic-artifact-other", "synthetic-artifact-outsider")
    outsider = execute_campaign_pair(other.pairs[0], completed_attempt)
    with pytest.raises(StatisticalRouteBenchArtifactError, match="not part"):
        store.write_record(outsider)
    ledger = run_campaign_to_artifacts(other, completed_attempt, tmp_path).ledger
    with pytest.raises(StatisticalRouteBenchArtifactError, match="escaped"):
        store.write_ledger(ledger)


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        (lambda item: item.update(arm_role="other"), "role or outcome"),
        (lambda item: item.update(outcome="other"), "role or outcome"),
        (lambda item: item.update(extra=True), "fields drifted"),
        (lambda item: item.update(event_ids={}), "string array"),
        (lambda item: item.update(stream_realization_digests={}), "must be an array"),
        (
            lambda item: item.update(stream_realization_digests=[["demand"]]),
            "entries are invalid",
        ),
        (lambda item: item.update(attempt=True), "must be an integer"),
        (lambda item: item.update(runtime_millis=True), "must be numeric"),
        (lambda item: item.update(failure_code=""), "null or non-blank"),
    ),
)
def test_attempt_artifact_parser_rejects_type_and_field_drift(
    mutation: Mutation, message: str
) -> None:
    pair = plan().pairs[0]
    payload = json.loads(json.dumps(completed_attempt(pair, "candidate", 1).payload()))
    mutation(payload)
    with pytest.raises(StatisticalRouteBenchArtifactError, match=message):
        artifacts._parse_attempt(payload)


def test_json_artifact_helpers_reject_drift_and_unreadable_inputs(tmp_path: Path) -> None:
    path = tmp_path / "artifact.json"
    artifacts._write_or_verify_json(path, {"value": "one"})
    with pytest.raises(StatisticalRouteBenchArtifactError, match="already differs"):
        artifacts._write_or_verify_json(path, {"value": "two"})
    path.with_suffix(".json.sha256").write_text("b" * 64 + "\n", encoding="ascii")
    with pytest.raises(StatisticalRouteBenchArtifactError, match="sidecar differs"):
        artifacts._write_or_verify_json(path, {"value": "one"})

    missing = tmp_path / "missing.json"
    with pytest.raises(StatisticalRouteBenchArtifactError, match="unreadable"):
        artifacts._read_verified_json(missing)
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{", encoding="utf-8")
    invalid.with_suffix(".json.sha256").write_text(
        sha256(b"{").hexdigest() + "\n", encoding="ascii"
    )
    with pytest.raises(StatisticalRouteBenchArtifactError, match="unreadable"):
        artifacts._read_verified_json(invalid)


def test_artifact_scalar_helpers_reject_non_objects_and_blank_values() -> None:
    with pytest.raises(StatisticalRouteBenchArtifactError, match="must be an object"):
        artifacts._mapping([], "value")
    with pytest.raises(StatisticalRouteBenchArtifactError, match="fields drifted"):
        artifacts._exact_keys({"a": 1}, {"b"}, "value")
    with pytest.raises(StatisticalRouteBenchArtifactError, match="non-blank string"):
        artifacts._string({"value": ""}, "value")


def test_pilot_analysis_artifact_is_bound_to_plan_and_write_once(tmp_path: Path) -> None:
    protocol = replace(
        load_statistical_routebench_protocol(PROTOCOL_PATH),
        protocol_id="synthetic-artifact-validation",
    )
    campaign = plan()
    ledger = execute_campaign(campaign, completed_attempt)
    analysis = analyze_pilot_campaign(protocol, campaign, ledger)

    path = write_pilot_analysis_artifact(campaign, analysis, tmp_path)

    assert path.name == "pilot-analysis.json"
    assert path.with_suffix(".json.sha256").is_file()
    assert write_pilot_analysis_artifact(campaign, analysis, tmp_path) == path
    store = CampaignArtifactStore(
        tmp_path, campaign, CampaignExecutionEnvironment.capture(campaign)
    )
    with pytest.raises(StatisticalRouteBenchArtifactError, match="escaped"):
        store.write_pilot_analysis(replace(analysis, campaign_plan_digest="b" * 64))
