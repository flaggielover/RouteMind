from __future__ import annotations

import json
import subprocess
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from routemind_compute.application import statistical_routebench_runner as runner
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
REVISION = "1" * 40
CI_RUN = 123456


def checkpoint_command(
    directory: Path, *command: str, head: str = REVISION, conclusion: str = "success"
) -> str:
    del directory
    if command[0:3] == ("git", "rev-parse", "HEAD"):
        return head
    if command[0:3] == ("git", "rev-parse", "origin/main"):
        return head
    if command[0:3] == ("git", "branch", "--show-current"):
        return "main"
    if command[0:3] == ("git", "status", "--porcelain"):
        return ""
    if command[0:3] == ("gh", "run", "view"):
        return json.dumps(
            {
                "databaseId": CI_RUN,
                "headSha": head,
                "status": "completed",
                "conclusion": conclusion,
                "workflowName": "CI",
            }
        )
    raise AssertionError(command)


def test_checkpoint_requires_head_origin_main_clean_main_and_green_github_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner, "_command", checkpoint_command)
    assert runner._verified_implementation_checkpoint(ROOT, REVISION, CI_RUN) == REVISION


@pytest.mark.parametrize(
    ("override", "value"),
    (
        ("head", "2" * 40),
        ("origin", "2" * 40),
        ("branch", "feature"),
        ("status", " M tracked.py"),
        ("ci_head", "2" * 40),
        ("ci_status", "in_progress"),
        ("conclusion", "failure"),
    ),
)
def test_checkpoint_rejects_local_or_remote_drift(
    monkeypatch: pytest.MonkeyPatch, override: str, value: str
) -> None:
    def command(directory: Path, *arguments: str) -> str:
        del directory
        if arguments[0:3] == ("git", "rev-parse", "HEAD"):
            return value if override == "head" else REVISION
        if arguments[0:3] == ("git", "rev-parse", "origin/main"):
            return value if override == "origin" else REVISION
        if arguments[0:3] == ("git", "branch", "--show-current"):
            return value if override == "branch" else "main"
        if arguments[0:3] == ("git", "status", "--porcelain"):
            return value if override == "status" else ""
        return json.dumps(
            {
                "databaseId": CI_RUN,
                "headSha": value if override == "ci_head" else REVISION,
                "status": value if override == "ci_status" else "completed",
                "conclusion": value if override == "conclusion" else "success",
                "workflowName": "CI",
            }
        )

    monkeypatch.setattr(runner, "_command", command)
    with pytest.raises(
        runner.StatisticalRouteBenchRunnerError, match=r"requires|does not authorize"
    ):
        runner._verified_implementation_checkpoint(ROOT, REVISION, CI_RUN)


def test_checkpoint_rejects_invalid_github_json(monkeypatch: pytest.MonkeyPatch) -> None:
    def command(directory: Path, *arguments: str) -> str:
        if arguments[0] == "gh":
            return "{"
        return checkpoint_command(directory, *arguments)

    monkeypatch.setattr(runner, "_command", command)
    with pytest.raises(runner.StatisticalRouteBenchRunnerError, match="invalid JSON"):
        runner._verified_implementation_checkpoint(ROOT, REVISION, CI_RUN)


def test_runner_main_builds_guarded_pilot_and_reports_artifact_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    protocol = replace(
        load_statistical_routebench_protocol(PROTOCOL_PATH),
        protocol_id="synthetic-runner-validation",
    )
    captured: dict[str, object] = {}

    def fake_run(plan: object, executor: object, data_root: Path) -> object:
        captured.update(plan=plan, executor=executor, data_root=data_root)
        ledger = SimpleNamespace(
            ledger_digest="a" * 64,
            disposition="PILOT_COMPLETE_FOR_VARIANCE_ONLY",
            complete_pair_count=64,
            retained_attempt_count=128,
        )
        return SimpleNamespace(
            ledger=ledger,
            artifact_bytes=1234,
            output_directory=tmp_path / "output",
        )

    monkeypatch.setattr(runner, "_git_repository", lambda: ROOT)
    monkeypatch.setattr(runner, "_verified_implementation_checkpoint", lambda *_: REVISION)
    monkeypatch.setattr(runner, "load_statistical_routebench_protocol", lambda _: protocol)
    monkeypatch.setattr(runner, "run_campaign_to_artifacts", fake_run)
    analysis = SimpleNamespace(
        analysis_digest="b" * 64,
        disposition="CONFIRMATORY_DESIGN_READY",
        confirmatory_pairs_per_regime=20,
        power_plans=(),
    )
    monkeypatch.setattr(runner, "analyze_pilot_campaign", lambda *_: analysis)
    monkeypatch.setattr(
        runner,
        "write_pilot_analysis_artifact",
        lambda *_: tmp_path / "pilot-analysis.json",
    )

    assert (
        runner.main(
            [
                "--protocol",
                str(PROTOCOL_PATH),
                "--data-root",
                str(tmp_path),
                "--campaign-id",
                "synthetic-runner-campaign",
                "--implementation-revision",
                REVISION,
                "--implementation-ci-run",
                str(CI_RUN),
                "--authorized-at-utc",
                "2026-08-24T12:00:00Z",
            ]
        )
        == 0
    )
    output = json.loads(capsys.readouterr().out)
    assert output["complete_pair_count"] == 64
    assert output["ledger_digest"] == "a" * 64
    assert output["pilot_analysis_digest"] == "b" * 64
    assert captured["data_root"] == tmp_path


def test_runner_stops_confirmatory_execution_when_pilot_power_is_non_estimable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    protocol = replace(
        load_statistical_routebench_protocol(PROTOCOL_PATH),
        protocol_id="synthetic-runner-blocked",
    )
    ledger = SimpleNamespace(
        ledger_digest="a" * 64,
        disposition="PILOT_COMPLETE_FOR_VARIANCE_ONLY",
        complete_pair_count=64,
        retained_attempt_count=128,
    )
    result = SimpleNamespace(
        ledger=ledger,
        artifact_bytes=1234,
        output_directory=tmp_path / "pilot",
    )
    analysis = SimpleNamespace(
        analysis_digest="b" * 64,
        disposition="CONFIRMATORY_BLOCKED_NON_ESTIMABLE_PILOT_RETAINED",
        confirmatory_pairs_per_regime=None,
        power_plans=(),
    )
    monkeypatch.setattr(runner, "_git_repository", lambda: ROOT)
    monkeypatch.setattr(runner, "_verified_implementation_checkpoint", lambda *_: REVISION)
    monkeypatch.setattr(runner, "load_statistical_routebench_protocol", lambda _: protocol)
    monkeypatch.setattr(runner, "run_campaign_to_artifacts", lambda *_: result)
    monkeypatch.setattr(runner, "analyze_pilot_campaign", lambda *_: analysis)
    monkeypatch.setattr(
        runner,
        "write_pilot_analysis_artifact",
        lambda *_: tmp_path / "pilot-analysis.json",
    )

    code = runner.main(
        [
            "--protocol",
            str(PROTOCOL_PATH),
            "--data-root",
            str(tmp_path),
            "--campaign-id",
            "synthetic-runner-pilot",
            "--confirmatory-campaign-id",
            "synthetic-runner-confirmatory",
            "--implementation-revision",
            REVISION,
            "--implementation-ci-run",
            str(CI_RUN),
        ]
    )

    assert code == 2
    assert json.loads(capsys.readouterr().out)["pilot_analysis_disposition"].startswith(
        "CONFIRMATORY_BLOCKED"
    )


def test_runner_executes_confirmatory_only_after_ready_pilot_analysis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    protocol = replace(
        load_statistical_routebench_protocol(PROTOCOL_PATH),
        protocol_id="synthetic-runner-ready",
    )
    pilot_ledger = SimpleNamespace(
        ledger_digest="a" * 64,
        disposition="PILOT_COMPLETE_FOR_VARIANCE_ONLY",
        complete_pair_count=64,
        retained_attempt_count=128,
    )
    confirmatory_ledger = SimpleNamespace(
        ledger_digest="c" * 64,
        disposition="CONFIRMATORY_COMPLETE_FOR_FROZEN_ANALYSIS",
        complete_pair_count=160,
        retained_attempt_count=320,
    )
    results = iter(
        (
            SimpleNamespace(
                ledger=pilot_ledger,
                artifact_bytes=1234,
                output_directory=tmp_path / "pilot",
            ),
            SimpleNamespace(
                ledger=confirmatory_ledger,
                artifact_bytes=5678,
                output_directory=tmp_path / "confirmatory",
            ),
        )
    )
    analysis = SimpleNamespace(
        analysis_digest="b" * 64,
        disposition="CONFIRMATORY_DESIGN_READY",
        confirmatory_pairs_per_regime=20,
        power_plans=(object(),),
    )
    confirmatory_plan = SimpleNamespace(
        campaign_id="synthetic-runner-confirmatory",
        plan_digest="d" * 64,
    )
    monkeypatch.setattr(runner, "_git_repository", lambda: ROOT)
    monkeypatch.setattr(runner, "_verified_implementation_checkpoint", lambda *_: REVISION)
    monkeypatch.setattr(runner, "load_statistical_routebench_protocol", lambda _: protocol)
    monkeypatch.setattr(runner, "run_campaign_to_artifacts", lambda *_: next(results))
    monkeypatch.setattr(runner, "analyze_pilot_campaign", lambda *_: analysis)
    monkeypatch.setattr(runner, "write_pilot_analysis_artifact", lambda *_: tmp_path / "analysis")
    monkeypatch.setattr(runner, "build_confirmatory_campaign_plan", lambda *_: confirmatory_plan)

    code = runner.main(
        [
            "--protocol",
            str(PROTOCOL_PATH),
            "--data-root",
            str(tmp_path),
            "--campaign-id",
            "synthetic-runner-pilot",
            "--confirmatory-campaign-id",
            "synthetic-runner-confirmatory",
            "--implementation-revision",
            REVISION,
            "--implementation-ci-run",
            str(CI_RUN),
        ]
    )

    assert code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["confirmatory"]["ledger_digest"] == "c" * 64


def test_command_and_repository_discovery_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failed(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise subprocess.CalledProcessError(1, "git")

    monkeypatch.setattr(subprocess, "run", failed)
    with pytest.raises(runner.StatisticalRouteBenchRunnerError, match="command failed"):
        runner._command(tmp_path, "git", "rev-parse", "HEAD")

    monkeypatch.setattr(runner, "_command", lambda *_: str(tmp_path))
    with pytest.raises(runner.StatisticalRouteBenchRunnerError, match="RouteMind repository"):
        runner._git_repository()


def test_command_returns_trimmed_output_and_parser_uses_environment_data_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    completed = subprocess.CompletedProcess(("git",), 0, " value \n", "")
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: completed)
    assert runner._command(tmp_path, "git", "status") == "value"

    monkeypatch.setenv("ROUTEMIND_DATA_ROOT", str(tmp_path))
    arguments = runner._parser().parse_args(
        [
            "--campaign-id",
            "synthetic-runner-campaign",
            "--implementation-revision",
            REVISION,
            "--implementation-ci-run",
            str(CI_RUN),
        ]
    )
    assert arguments.data_root == tmp_path
    assert arguments.authorized_at_utc.endswith("Z")

    monkeypatch.setattr(runner, "_command", lambda *_: str(ROOT))
    assert runner._git_repository() == ROOT
