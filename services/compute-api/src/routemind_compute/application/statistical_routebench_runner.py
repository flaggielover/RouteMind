"""Guarded command-line runner for material Statistical RouteBench execution."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from routemind_compute.application.registry import default_registry
from routemind_compute.application.statistical_routebench_analysis import (
    analyze_pilot_campaign,
)
from routemind_compute.application.statistical_routebench_artifacts import (
    run_campaign_to_artifacts,
    write_pilot_analysis_artifact,
)
from routemind_compute.application.statistical_routebench_campaign import (
    CampaignAuthorization,
    build_confirmatory_campaign_plan,
    build_pilot_campaign_plan,
)
from routemind_compute.application.statistical_routebench_local import (
    FrozenLocalPilotArmExecutor,
)
from routemind_compute.application.statistical_routebench_protocol import (
    load_statistical_routebench_protocol,
)
from routemind_compute.application.travel import DeterministicLocalTravelProvider


class StatisticalRouteBenchRunnerError(ValueError):
    """Raised when the material execution checkpoint cannot be verified."""


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    repository = _git_repository()
    revision = _verified_implementation_checkpoint(
        repository, arguments.implementation_revision, arguments.implementation_ci_run
    )
    protocol = load_statistical_routebench_protocol(arguments.protocol.resolve())
    authorization = CampaignAuthorization(
        implementation_revision=revision,
        implementation_ci_run=arguments.implementation_ci_run,
        implementation_ci_conclusion="success",
        authorized_at_utc=arguments.authorized_at_utc,
    )
    plan = build_pilot_campaign_plan(protocol, arguments.campaign_id, authorization)
    executor = FrozenLocalPilotArmExecutor(
        protocol,
        default_registry(),
        DeterministicLocalTravelProvider(),
    )
    result = run_campaign_to_artifacts(plan, executor, arguments.data_root.resolve())
    analysis = analyze_pilot_campaign(protocol, plan, result.ledger)
    analysis_path = write_pilot_analysis_artifact(plan, analysis, arguments.data_root.resolve())
    pilot_artifact_bytes = sum(
        path.stat().st_size for path in result.output_directory.rglob("*") if path.is_file()
    )
    output: dict[str, object] = {
        "campaign_id": plan.campaign_id,
        "phase": plan.phase,
        "plan_digest": plan.plan_digest,
        "ledger_digest": result.ledger.ledger_digest,
        "disposition": result.ledger.disposition,
        "complete_pair_count": result.ledger.complete_pair_count,
        "retained_attempt_count": result.ledger.retained_attempt_count,
        "artifact_bytes": pilot_artifact_bytes,
        "output_directory": str(result.output_directory),
        "pilot_analysis_digest": analysis.analysis_digest,
        "pilot_analysis_disposition": analysis.disposition,
        "pilot_analysis_path": str(analysis_path),
        "confirmatory_pairs_per_regime": analysis.confirmatory_pairs_per_regime,
    }
    if arguments.confirmatory_campaign_id:
        if analysis.disposition != "CONFIRMATORY_DESIGN_READY":
            print(json.dumps(output, sort_keys=True))
            return 2
        confirmatory_plan = build_confirmatory_campaign_plan(
            protocol,
            arguments.confirmatory_campaign_id,
            authorization,
            result.ledger.ledger_digest,
            analysis.power_plans,
        )
        confirmatory = run_campaign_to_artifacts(
            confirmatory_plan, executor, arguments.data_root.resolve()
        )
        output["confirmatory"] = {
            "campaign_id": confirmatory_plan.campaign_id,
            "plan_digest": confirmatory_plan.plan_digest,
            "ledger_digest": confirmatory.ledger.ledger_digest,
            "disposition": confirmatory.ledger.disposition,
            "complete_pair_count": confirmatory.ledger.complete_pair_count,
            "retained_attempt_count": confirmatory.ledger.retained_attempt_count,
            "artifact_bytes": confirmatory.artifact_bytes,
            "output_directory": str(confirmatory.output_directory),
        }
    print(json.dumps(output, sort_keys=True))
    return 0


def _verified_implementation_checkpoint(
    repository: Path,
    requested_revision: str,
    ci_run: int,
) -> str:
    head = _command(repository, "git", "rev-parse", "HEAD")
    origin_main = _command(repository, "git", "rev-parse", "origin/main")
    branch = _command(repository, "git", "branch", "--show-current")
    tracked_status = _command(repository, "git", "status", "--porcelain", "--untracked-files=no")
    if (
        head != requested_revision
        or origin_main != requested_revision
        or branch != "main"
        or tracked_status
    ):
        raise StatisticalRouteBenchRunnerError(
            "material execution requires clean tracked main at the requested origin/main revision"
        )
    try:
        run = json.loads(
            _command(
                repository,
                "gh",
                "run",
                "view",
                str(ci_run),
                "--json",
                "databaseId,headSha,status,conclusion,workflowName",
            )
        )
    except json.JSONDecodeError as error:
        raise StatisticalRouteBenchRunnerError("GitHub Actions returned invalid JSON") from error
    if (
        not isinstance(run, dict)
        or run.get("databaseId") != ci_run
        or run.get("headSha") != requested_revision
        or run.get("status") != "completed"
        or run.get("conclusion") != "success"
    ):
        raise StatisticalRouteBenchRunnerError(
            "GitHub Actions run does not authorize this implementation revision"
        )
    return head


def _git_repository() -> Path:
    root = _command(Path.cwd(), "git", "rev-parse", "--show-toplevel")
    repository = Path(root).resolve()
    if not (repository / "AGENTS.md").is_file():
        raise StatisticalRouteBenchRunnerError("runner must execute from the RouteMind repository")
    return repository


def _command(directory: Path, *command: str) -> str:
    try:
        completed = subprocess.run(
            command,
            cwd=directory,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise StatisticalRouteBenchRunnerError(
            f"checkpoint command failed: {' '.join(command[:3])}"
        ) from error
    return completed.stdout.strip()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the frozen R3-325 Statistical RouteBench pilot"
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path(
            "docs/research/r3/manifests/statistical-routebench/statistical-routebench-v1.json"
        ),
    )
    configured_root = os.getenv("ROUTEMIND_DATA_ROOT")
    parser.add_argument(
        "--data-root",
        type=Path,
        required=configured_root is None,
        default=Path(configured_root) if configured_root else None,
    )
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--confirmatory-campaign-id")
    parser.add_argument("--implementation-revision", required=True)
    parser.add_argument("--implementation-ci-run", required=True, type=int)
    parser.add_argument(
        "--authorized-at-utc",
        default=datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
    )
    return parser


__all__ = ["StatisticalRouteBenchRunnerError", "main"]
