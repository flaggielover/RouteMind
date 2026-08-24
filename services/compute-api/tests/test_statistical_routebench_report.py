from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from routemind_compute.application import statistical_routebench_report_cli as report_cli
from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.statistical_routebench_analysis import (
    analyze_pilot_campaign,
)
from routemind_compute.application.statistical_routebench_artifacts import (
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
)
from routemind_compute.application.statistical_routebench_protocol import (
    StatisticalRouteBenchProtocol,
    load_statistical_routebench_protocol,
)
from routemind_compute.application.statistical_routebench_report import (
    StatisticalRouteBenchReportError,
    build_statistical_routebench_report,
    write_statistical_routebench_report,
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
STREAMS = tuple((name, "a" * 64) for name in ("demand", "merchant", "courier", "traffic"))


def _campaign() -> tuple[StatisticalRouteBenchProtocol, StatisticalRouteBenchCampaignPlan]:
    protocol = load_statistical_routebench_protocol(PROTOCOL_PATH)
    plan = build_pilot_campaign_plan(
        protocol,
        "report-fixture-campaign",
        CampaignAuthorization("1" * 40, 123456, "success", "2026-08-24T12:00:00Z"),
    )
    return protocol, plan


def _attempt(pair: PilotPairExecutionPlan, role: ArmRole, number: int) -> ArmExecutionAttempt:
    replicate = pair.randomness.pair.replicate
    candidate = role == "candidate"
    return ArmExecutionAttempt(
        pair_plan_digest=pair.pair_plan_digest,
        arm_role=role,
        strategy=pair.candidate_strategy if candidate else pair.comparator_strategy,
        strategy_version="1.0.0",
        attempt=number,
        outcome="COMPLETED",
        started_at_utc="2026-08-24T12:00:00.000Z",
        completed_at_utc="2026-08-24T12:00:00.001Z",
        request_count=2,
        assigned_count=1 + (replicate % 2 if candidate else 0),
        scenario_risk_index=(0.20 + 0.01 * replicate if candidate else 0.40 + 0.02 * replicate),
        assignment_rate=(1 + (replicate % 2 if candidate else 0)) / 2,
        runtime_millis=1.0 + replicate + (0.5 if candidate else 0.0),
        strategy_failure_count=0,
        fallback_count=0,
        timeout_count=0,
        event_ids=(f"{pair.randomness.pair.regime_id}-{replicate}-0", "event-1"),
        scenario_manifest_digest="b" * 64,
        stream_realization_digests=STREAMS,
        deterministic_result_digest=canonical_digest([pair.pair_plan_digest, role, replicate]),
    )


def _materialize(tmp_path: Path) -> Path:
    protocol, plan = _campaign()
    result = run_campaign_to_artifacts(plan, _attempt, tmp_path)
    analysis = analyze_pilot_campaign(protocol, plan, result.ledger)
    write_pilot_analysis_artifact(plan, analysis, tmp_path)
    return result.output_directory


def test_report_recomputes_distributions_lineage_and_negative_boundary(tmp_path: Path) -> None:
    directory = _materialize(tmp_path)
    report = build_statistical_routebench_report(directory, PROTOCOL_PATH)

    assert len(report.cells) == 16
    assert all(cell["n"] == 8 for cell in report.cells)
    assert all(len(cast(list[object], cell["pair_seeds"])) == 8 for cell in report.cells)
    assert report.multiplicity["family_size"] == 16
    assert report.multiplicity["disposition"] == "CONFIRMATORY_NOT_EXECUTED"
    assert report.diagnostics["arm_count"] == 128
    assert report.report_digest == canonical_digest(report.payload())

    path = write_statistical_routebench_report(report, directory)
    assert path.is_file()
    assert path.with_suffix(path.suffix + ".sha256").is_file()
    assert write_statistical_routebench_report(report, directory) == path


def test_report_rejects_tampered_source_before_reinterpretation(tmp_path: Path) -> None:
    directory = _materialize(tmp_path)
    ledger = directory / "campaign-ledger.json"
    payload = json.loads(ledger.read_text(encoding="utf-8"))
    payload["ledger"]["disposition"] = "FORGED"
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    ledger.write_bytes(encoded)
    with pytest.raises(StatisticalRouteBenchReportError, match="checksum mismatch"):
        build_statistical_routebench_report(directory, PROTOCOL_PATH)


def test_report_rejects_missing_pair_sidecar(tmp_path: Path) -> None:
    directory = _materialize(tmp_path)
    sidecar = next((directory / "pairs").glob("*.json.sha256"))
    sidecar.unlink()
    with pytest.raises(StatisticalRouteBenchReportError, match=r"checksum|sidecar"):
        build_statistical_routebench_report(directory, PROTOCOL_PATH)


def test_report_rejects_wrong_protocol_manifest(tmp_path: Path) -> None:
    directory = _materialize(tmp_path)
    wrong = tmp_path / "wrong.json"
    wrong.write_text(
        PROTOCOL_PATH.read_text(encoding="utf-8").replace("R3-320", "R3-999"), encoding="utf-8"
    )
    with pytest.raises(ValueError, match=r"protocol|manifest|content|task identity"):
        build_statistical_routebench_report(directory, wrong)


def test_report_cli_prints_content_addressed_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    directory = _materialize(tmp_path)
    report = build_statistical_routebench_report(directory, PROTOCOL_PATH)
    monkeypatch.setattr(report_cli, "build_statistical_routebench_report", lambda *_: report)
    monkeypatch.setattr(
        report_cli, "write_statistical_routebench_report", lambda *_: directory / "report.json"
    )
    assert report_cli.main(["--data-root", str(tmp_path), "--campaign-id", directory.name]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["cell_count"] == 16
    assert output["report_digest"] == report.report_digest
