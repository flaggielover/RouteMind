from __future__ import annotations

import argparse
import json
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from .artifacts import ArtifactClass, ArtifactStore
from .gate2 import run_gate2
from .identification import identify_layer
from .negative_control import run_negative_control_diagnostic
from .preregistration import Preregistration, canonical_json
from .reason_codes import ResearchGateError
from .records import Trajectory
from .reduced_model import ReducedModel
from .short_horizon import generate_short_horizon

PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[2]
PREREGISTRATION_PATH = PACKAGE_ROOT / "configs" / "preregistration.json"
PREREGISTRATION_DIGEST_PATH = PACKAGE_ROOT / "configs" / "preregistration.sha256"


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _load_preregistration() -> Preregistration:
    preregistration = Preregistration.load(PREREGISTRATION_PATH)
    try:
        expected = PREREGISTRATION_DIGEST_PATH.read_text(encoding="ascii").split()[0]
    except OSError as exc:
        raise ResearchGateError("CONFIG_DIGEST_MISMATCH", str(exc)) from exc
    if preregistration.digest != expected:
        raise ResearchGateError(
            "CONFIG_DIGEST_MISMATCH",
            f"expected {expected}, observed {preregistration.digest}",
        )
    return preregistration


def verify_preregistration() -> dict[str, object]:
    preregistration = _load_preregistration()
    return {
        "status": "PASS",
        "experiment_id": preregistration.payload["experiment_id"],
        "preregistration_digest": preregistration.digest,
        "path": str(PREREGISTRATION_PATH.relative_to(REPOSITORY_ROOT)).replace(
            "\\", "/"
        ),
    }


def _trajectory_payload(
    trajectories: tuple[Trajectory, ...],
) -> list[dict[str, object]]:
    return [item.payload() for item in trajectories]


def _number(payload: dict[str, object], name: str) -> float:
    value = payload.get(name)
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ResearchGateError("CONFIG_INVALID", f"{name} must be numeric")
    return float(value)


def identify(*, diagnostic: bool) -> dict[str, object]:
    preregistration = _load_preregistration()
    identification = preregistration.payload["identification"]
    gates = preregistration.payload["gates"]
    layer_r_config = preregistration.payload["layer_r"]
    layer_m_config = preregistration.payload["layer_m"]
    if not isinstance(identification, dict) or not isinstance(gates, dict):
        raise ResearchGateError("CONFIG_INVALID")
    if not isinstance(layer_r_config, dict) or not isinstance(layer_m_config, dict):
        raise ResearchGateError("CONFIG_INVALID")
    typed_identification = cast(dict[str, object], identification)
    typed_gates = cast(dict[str, object], gates)
    typed_r = cast(dict[str, object], layer_r_config)
    typed_m = cast(dict[str, object], layer_m_config)
    artifact_class: ArtifactClass = "diagnostic" if diagnostic else "confirmatory"
    layer_r, layer_m = generate_short_horizon(
        preregistration.payload, diagnostic=diagnostic
    )
    reduced = ReducedModel.from_config(typed_r)
    bootstrap_resamples = (
        min(100, int(_number(typed_identification, "bootstrap_resamples")))
        if diagnostic
        else int(_number(typed_identification, "bootstrap_resamples"))
    )
    estimate_r = identify_layer(
        layer_r,
        probe_alpha=0.35,
        bootstrap_resamples=bootstrap_resamples,
        bootstrap_seed=int(_number(typed_identification, "bootstrap_seed")),
        gates=typed_gates,
        true_a=reduced.a,
        true_m=reduced.m,
    )
    estimate_m = identify_layer(
        layer_m,
        probe_alpha=0.35,
        bootstrap_resamples=bootstrap_resamples,
        bootstrap_seed=int(_number(typed_identification, "bootstrap_seed")) + 1,
        gates=typed_gates,
    )
    store = ArtifactStore.from_environment()
    run_id = "short-horizon-v1" if not diagnostic else "short-horizon-diagnostic-v1"
    raw = {
        "experiment_id": preregistration.payload["experiment_id"],
        "artifact_class": artifact_class,
        "run_id": run_id,
        "preregistration_digest": preregistration.digest,
        "layer_r": _trajectory_payload(layer_r),
        "layer_m": _trajectory_payload(layer_m),
    }
    raw_artifact = store.write_json(
        artifact_class, f"identification/{run_id}-trajectories.json", raw
    )
    status = "PASS" if estimate_r.gate.passed and estimate_m.gate.passed else "FAIL"
    summary = {
        "experiment_id": preregistration.payload["experiment_id"],
        "artifact_class": artifact_class,
        "stage": "short-horizon-identification",
        "run_id": run_id,
        "status": status,
        "preregistration_digest": preregistration.digest,
        "implementation_commit": _git("rev-parse", "HEAD"),
        "worktree_disclosure": _git("status", "--short", "--untracked-files=all"),
        "generated_at": datetime.now(UTC).isoformat(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "identification_horizon": typed_identification["horizon"],
        "seeds": typed_identification["seeds"]
        if not diagnostic
        else cast(list[object], typed_identification["seeds"])[:4],
        "bootstrap_resamples": bootstrap_resamples,
        "model_versions": {
            "layer_r": typed_r["model_version"],
            "layer_m": typed_m["model_version"],
            "estimator": "local-rank-one-v1",
        },
        "raw_artifact": {
            "relative_path": raw_artifact.relative_path,
            "sha256": raw_artifact.sha256,
            "content_digest": raw_artifact.content_digest,
        },
        "layer_r": estimate_r.payload(),
        "layer_m": estimate_m.payload(),
    }
    summary_artifact = store.write_json(
        artifact_class, f"identification/{run_id}-summary.json", summary
    )
    return {
        "status": status,
        "artifact_class": artifact_class,
        "summary_relative_path": summary_artifact.relative_path,
        "summary_sha256": summary_artifact.sha256,
        "summary_content_digest": summary_artifact.content_digest,
        "layer_r_gate": estimate_r.gate.payload(),
        "layer_m_gate": estimate_m.gate.payload(),
    }


def freeze_threshold() -> dict[str, object]:
    preregistration = _load_preregistration()
    store = ArtifactStore.from_environment()
    summary_path = "identification/short-horizon-v1-summary.json"
    summary, summary_artifact = store.read_json("confirmatory", summary_path)
    if summary.get("preregistration_digest") != preregistration.digest:
        raise ResearchGateError("CONFIG_DIGEST_MISMATCH", summary_path)
    if summary.get("artifact_class") != "confirmatory":
        raise ResearchGateError("ARTIFACT_CLASS_MISMATCH", summary_path)
    layer_r = summary.get("layer_r")
    layer_m = summary.get("layer_m")
    if not isinstance(layer_r, dict) or not isinstance(layer_m, dict):
        raise ResearchGateError("ARTIFACT_DIGEST_MISMATCH", "missing layer estimates")
    status = str(summary.get("status"))
    frozen = {
        "experiment_id": preregistration.payload["experiment_id"],
        "artifact_class": "confirmatory",
        "stage": "frozen-threshold-prediction",
        "status": status,
        "preregistration_digest": preregistration.digest,
        "implementation_commit": summary["implementation_commit"],
        "worktree_disclosure_at_identification": summary["worktree_disclosure"],
        "model_versions": summary["model_versions"],
        "identification_horizon": summary["identification_horizon"],
        "seeds": summary["seeds"],
        "source_summary": {
            "relative_path": summary_artifact.relative_path,
            "sha256": summary_artifact.sha256,
            "content_digest": summary_artifact.content_digest,
        },
        "predictions": {
            "layer_r": {
                "kappa": layer_r["kappa"],
                "kappa_ci95": layer_r["kappa_ci95"],
                "predicted_alpha_c": layer_r["alpha_c"],
                "alpha_c_ci95": layer_r["alpha_c_ci95"],
                "gate": layer_r["gate"],
            },
            "layer_m": {
                "kappa": layer_m["kappa"],
                "kappa_ci95": layer_m["kappa_ci95"],
                "predicted_alpha_c": layer_m["alpha_c"],
                "alpha_c_ci95": layer_m["alpha_c_ci95"],
                "gate": layer_m["gate"],
            },
        },
        "generated_at": datetime.now(UTC).isoformat(),
        "freeze_policy": "exclusive-create; no withheld long-horizon input",
    }
    artifact = store.write_json(
        "confirmatory", "threshold/frozen-prediction-v1.json", frozen
    )
    return {
        "status": status,
        "relative_path": artifact.relative_path,
        "sha256": artifact.sha256,
        "content_digest": artifact.content_digest,
        "frozen_prediction": frozen,
    }


def verify_frozen() -> dict[str, object]:
    preregistration = _load_preregistration()
    payload, artifact = ArtifactStore.from_environment().read_json(
        "confirmatory", "threshold/frozen-prediction-v1.json"
    )
    if payload.get("preregistration_digest") != preregistration.digest:
        raise ResearchGateError("CONFIG_DIGEST_MISMATCH")
    return {
        "status": payload.get("status"),
        "relative_path": artifact.relative_path,
        "sha256": artifact.sha256,
        "content_digest": artifact.content_digest,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RouteMind spatial lock-in Gate")
    parser.add_argument(
        "command",
        choices=(
            "verify-preregistration",
            "identify-confirmatory",
            "identify-diagnostic",
            "freeze-threshold",
            "verify-frozen-threshold",
            "run-gate2",
            "run-negative-control-diagnostic",
        ),
    )
    return parser


def main() -> int:
    arguments = _parser().parse_args()
    try:
        if arguments.command == "verify-preregistration":
            result = verify_preregistration()
        elif arguments.command == "identify-confirmatory":
            result = identify(diagnostic=False)
        elif arguments.command == "identify-diagnostic":
            result = identify(diagnostic=True)
        elif arguments.command == "freeze-threshold":
            result = freeze_threshold()
        elif arguments.command == "verify-frozen-threshold":
            result = verify_frozen()
        else:
            preregistration = _load_preregistration()
            store = ArtifactStore.from_environment()
            if arguments.command == "run-gate2":
                result = run_gate2(PACKAGE_ROOT, preregistration, store)
            else:
                result = run_negative_control_diagnostic(
                    PACKAGE_ROOT, preregistration, store
                )
    except ResearchGateError as exc:
        print(
            canonical_json(
                {
                    "status": "ERROR",
                    "reason_code": exc.reason.code,
                    "detail": exc.detail,
                }
            )
        )
        return 2
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
