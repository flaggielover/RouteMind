from __future__ import annotations

import hashlib
import platform
import random
import subprocess
from datetime import UTC, datetime
from math import isfinite, tanh
from pathlib import Path
from statistics import fmean
from typing import cast

from .artifacts import ArtifactStore, StoredArtifact
from .gate2b_protocol import Gate2bProtocol, load_gate2b_protocol
from .linalg import Matrix, Vector, matvec
from .mechanism import DeliveryMechanism, MechanismRun
from .preregistration import Preregistration
from .reason_codes import ResearchGateError
from .reduced_model import ReducedModel
from .stochastic_equilibrium import (
    AlphaRegime,
    ClassifiedRun,
    EquilibriumStatistics,
    aggregate_alpha,
    classify_states,
    observed_transition,
    percentile_interval,
    select_coarse_bracket,
    wilson_interval,
)

GATE_ROOT = "gate2b_stochastic_equilibrium"
CALIBRATION_PATH = f"{GATE_ROOT}/controls/calibration/results.json"
HOLDOUT_PATH = f"{GATE_ROOT}/controls/holdout/results.json"
REPLAY_PATH = f"{GATE_ROOT}/replay/replay.json"
VALIDATION_PATH = f"{GATE_ROOT}/reports/gate2b_validation.json"
INITIALS: tuple[tuple[str, Vector], ...] = (
    ("zero", (0.0, 0.0, 0.0)),
    ("positive", (0.01, 0.01, 0.01)),
    ("negative", (-0.01, -0.01, -0.01)),
)
REPLAY_SEEDS = (51000, 51001, 51031, 51063)
IMPLEMENTATION_FILES = (
    "artifacts.py",
    "gate2b.py",
    "gate2b_protocol.py",
    "mechanism.py",
    "reason_codes.py",
    "reduced_model.py",
    "run.py",
    "stochastic_equilibrium.py",
)


def _git(repository_root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ResearchGateError("GATE2B_NONFINITE", name)
    result = float(value)
    if not isfinite(result):
        raise ResearchGateError("GATE2B_NONFINITE", name)
    return result


def _integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ResearchGateError("GATE2B_FROZEN_INPUT_MISMATCH", name)
    return value


def _mapping(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ResearchGateError("GATE2B_FROZEN_INPUT_MISMATCH", name)
    return cast(dict[str, object], value)


def _list(value: object, name: str) -> list[object]:
    if not isinstance(value, list):
        raise ResearchGateError("GATE2B_FROZEN_INPUT_MISMATCH", name)
    return cast(list[object], value)


def _vector(value: object, name: str) -> Vector:
    items = _list(value, name)
    if len(items) != 3:
        raise ResearchGateError("GATE2B_FROZEN_INPUT_MISMATCH", name)
    return cast(Vector, tuple(_number(item, name) for item in items))


def _matrix(value: object, name: str) -> Matrix:
    rows = _list(value, name)
    if len(rows) != 3:
        raise ResearchGateError("GATE2B_FROZEN_INPUT_MISMATCH", name)
    return cast(Matrix, tuple(_vector(row, name) for row in rows))


def _range(section: dict[str, object], name: str) -> tuple[int, ...]:
    start = _integer(section.get("start"), f"{name}.start")
    end = _integer(section.get("end"), f"{name}.end")
    count = _integer(section.get("count"), f"{name}.count")
    values = tuple(range(start, end + 1))
    if len(values) != count:
        raise ResearchGateError("GATE2B_FROZEN_INPUT_MISMATCH", name)
    return values


def _implementation_digest(package_root: Path) -> str:
    digest = hashlib.sha256()
    paths = tuple(package_root / name for name in IMPLEMENTATION_FILES) + (
        package_root / "reports" / "GATE2B_STOCHASTIC_EQUILIBRIUM_PREREGISTRATION.json",
    )
    for path in paths:
        if not path.is_file():
            raise ResearchGateError("GATE2B_FROZEN_INPUT_MISMATCH", str(path))
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _metadata(package_root: Path, protocol: Gate2bProtocol) -> dict[str, object]:
    repository_root = package_root.parents[2]
    return {
        "protocol_id": protocol.payload["protocol_id"],
        "protocol_sha256": protocol.sha256,
        "implementation_digest": _implementation_digest(package_root),
        "execution_commit": _git(repository_root, "rev-parse", "HEAD"),
        "worktree_disclosure": _git(
            repository_root, "status", "--short", "--untracked-files=all"
        ),
        "generated_at": datetime.now(UTC).isoformat(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
    }


def verify_gate2b_preregistration(package_root: Path) -> dict[str, object]:
    protocol = load_gate2b_protocol(package_root)
    return {
        "status": "PASS",
        "protocol_id": protocol.payload["protocol_id"],
        "protocol_sha256": protocol.sha256,
        "implementation_digest": _implementation_digest(package_root),
        "interval_overlap_role": protocol.section("threshold_gate")[
            "identification_interval_overlap_role"
        ],
        "interval_overlap_is_pass_condition": False,
    }


def _verify_external_frozen(
    protocol: Gate2bProtocol, store: ArtifactStore
) -> dict[str, object]:
    frozen = protocol.section("frozen_inputs")
    expected = frozen.get("frozen_threshold_artifact_sha256")
    if not isinstance(expected, str):
        raise ResearchGateError("GATE2B_FROZEN_INPUT_MISMATCH", "frozen threshold hash")
    payload, artifact = store.read_json(
        "confirmatory",
        "threshold/frozen-prediction-v1.json",
        expected_sha256=expected,
    )
    if payload.get("status") != "PASS":
        raise ResearchGateError(
            "GATE2B_FROZEN_INPUT_MISMATCH", "Gate 1 threshold status"
        )
    return {
        "relative_path": artifact.relative_path,
        "sha256": artifact.sha256,
        "content_digest": artifact.content_digest,
    }


def _write(
    store: ArtifactStore, relative_path: str, payload: dict[str, object]
) -> StoredArtifact:
    target = store.resolve("confirmatory", relative_path)
    sidecar = target.with_suffix(target.suffix + ".sha256")
    if target.exists() or sidecar.exists():
        raise ResearchGateError("GATE2B_ARTIFACT_EXISTS", relative_path)
    return store.write_json("confirmatory", relative_path, payload)


def _read(store: ArtifactStore, path: str) -> tuple[dict[str, object], StoredArtifact]:
    return store.read_json("confirmatory", path)


def _require_stage_pass(
    store: ArtifactStore,
    path: str,
    implementation_digest: str,
) -> tuple[dict[str, object], StoredArtifact]:
    payload, artifact = _read(store, path)
    if payload.get("status") != "PASS":
        raise ResearchGateError("STAGE_ORDER_VIOLATION", f"{path} is not PASS")
    if payload.get("implementation_digest") != implementation_digest:
        raise ResearchGateError(
            "GATE2B_CONFIRMATORY_CONTAMINATION", "implementation digest changed"
        )
    return payload, artifact


def _simulate_linear(
    transition: Matrix,
    initial: Vector,
    *,
    horizon: int,
    seed: int,
    noise_sd: float,
) -> tuple[Vector, ...]:
    rng = random.Random(seed)
    states = [initial]
    for _ in range(horizon):
        core = matvec(transition, states[-1])
        states.append(
            cast(Vector, tuple(value + rng.gauss(0.0, noise_sd) for value in core))
        )
    return tuple(states)


def _simulate_locked(
    initial_z: float,
    *,
    state_map: Vector,
    horizon: int,
    seed: int,
    noise_sd: float,
) -> tuple[Vector, ...]:
    rng = random.Random(seed)
    z = initial_z
    states = [cast(Vector, tuple(z * value for value in state_map))]
    for _ in range(horizon):
        z = 0.90 * z + 0.12 * tanh(8.0 * z) + rng.gauss(0.0, noise_sd)
        states.append(cast(Vector, tuple(z * value for value in state_map)))
    return tuple(states)


def _control_gate(
    stable: tuple[ClassifiedRun, ...],
    locked: tuple[ClassifiedRun, ...],
    near_critical: tuple[ClassifiedRun, ...],
    seeds: tuple[int, ...],
) -> dict[str, object]:
    stable_restored = sum(item.label == "STOCHASTIC_RESTORED" for item in stable)
    stable_locked = sum(item.label == "LOCKED" for item in stable)
    by_key = {(item.seed, item.initial_id): item for item in locked}
    locked_pairs = 0
    locked_restored_paths = 0
    invalid_count = sum(
        item.label == "INVALID" for item in stable + locked + near_critical
    )
    for seed in seeds:
        positive = by_key[(seed, "positive")]
        negative = by_key[(seed, "negative")]
        if (
            positive.label == negative.label == "LOCKED"
            and positive.statistics.projection_mean
            * negative.statistics.projection_mean
            < 0.0
        ):
            locked_pairs += 1
        locked_restored_paths += sum(
            item.label == "STOCHASTIC_RESTORED" for item in (positive, negative)
        )
    near_transitional = sum(item.label == "TRANSITIONAL" for item in near_critical)
    stable_interval = wilson_interval(stable_restored, len(seeds))
    locked_interval = wilson_interval(locked_pairs, len(seeds))
    stable_sensitivity = stable_restored / len(seeds)
    locked_pair_sensitivity = locked_pairs / len(seeds)
    stable_false_positive = stable_locked / len(seeds)
    locked_false_negative = locked_restored_paths / (2 * len(seeds))
    near_transitional_rate = near_transitional / len(seeds)
    metrics = {
        "stable_sensitivity": stable_sensitivity,
        "stable_sensitivity_wilson95": stable_interval,
        "locked_pair_sensitivity": locked_pair_sensitivity,
        "locked_pair_sensitivity_wilson95": locked_interval,
        "stable_to_locked_false_positive_rate": stable_false_positive,
        "locked_to_restored_false_negative_rate": locked_false_negative,
        "near_critical_transitional_rate": near_transitional_rate,
        "invalid_count": invalid_count,
    }
    passed = (
        stable_sensitivity >= 0.95
        and stable_interval[0] >= 0.90
        and locked_pair_sensitivity >= 0.95
        and locked_interval[0] >= 0.90
        and stable_false_positive <= 0.01
        and locked_false_negative <= 0.01
        and near_transitional_rate >= 0.60
        and invalid_count == 0
    )
    return {"status": "PASS" if passed else "FAIL", "metrics": metrics}


def run_gate2b_control_stage(
    package_root: Path,
    store: ArtifactStore,
    *,
    stage: str,
) -> dict[str, object]:
    if stage not in {"calibration", "holdout"}:
        raise ResearchGateError("GATE2B_FROZEN_INPUT_MISMATCH", stage)
    protocol = load_gate2b_protocol(package_root)
    _verify_external_frozen(protocol, store)
    implementation = _implementation_digest(package_root)
    if stage == "calibration":
        gate_root = store.resolve("confirmatory", GATE_ROOT)
        if gate_root.exists():
            raise ResearchGateError("GATE2B_CONFIRMATORY_CONTAMINATION", str(gate_root))
    else:
        _require_stage_pass(store, CALIBRATION_PATH, implementation)
    controls = protocol.section("synthetic_controls")
    seed_key = "calibration_seeds" if stage == "calibration" else "holdout_seeds"
    seeds = _range(_mapping(controls.get(seed_key), seed_key), seed_key)
    families = _mapping(controls.get("families"), "families")
    stable_config = _mapping(families.get("stable"), "stable")
    locked_config = _mapping(families.get("locked"), "locked")
    near_config = _mapping(families.get("near_critical"), "near_critical")
    trajectory = protocol.section("trajectory_protocol")
    horizon = _integer(trajectory.get("horizon"), "horizon")
    weights = _vector(trajectory.get("projection_weights_l1_normalized"), "weights")
    stable: list[ClassifiedRun] = []
    locked: list[ClassifiedRun] = []
    near: list[ClassifiedRun] = []
    stable_matrix = _matrix(stable_config.get("transition_matrix"), "stable.matrix")
    near_matrix = _matrix(near_config.get("transition_matrix"), "near.matrix")
    state_map = _vector(locked_config.get("state_map"), "locked.state_map")
    paired = _list(locked_config.get("paired_initial_z"), "locked.paired_initial_z")
    for seed in seeds:
        stable_states = _simulate_linear(
            stable_matrix,
            _vector(stable_config.get("initial"), "stable.initial"),
            horizon=horizon,
            seed=seed,
            noise_sd=_number(stable_config.get("noise_sd"), "stable.noise_sd"),
        )
        stable.append(
            classify_states(
                "SYNTHETIC_STABLE", 0.0, 0.0, seed, "zero", stable_states, weights
            )
        )
        for initial_id, initial_z in zip(("positive", "negative"), paired, strict=True):
            locked_states = _simulate_locked(
                _number(initial_z, "locked.initial_z"),
                state_map=state_map,
                horizon=horizon,
                seed=seed,
                noise_sd=0.0005,
            )
            locked.append(
                classify_states(
                    "SYNTHETIC_LOCKED",
                    0.0,
                    0.0,
                    seed,
                    initial_id,
                    locked_states,
                    weights,
                )
            )
        near_states = _simulate_linear(
            near_matrix,
            _vector(near_config.get("initial"), "near.initial"),
            horizon=horizon,
            seed=seed,
            noise_sd=_number(near_config.get("noise_sd"), "near.noise_sd"),
        )
        near.append(
            classify_states(
                "SYNTHETIC_NEAR_CRITICAL",
                0.0,
                0.0,
                seed,
                "zero",
                near_states,
                weights,
            )
        )
    gate = _control_gate(tuple(stable), tuple(locked), tuple(near), seeds)
    payload = {
        **_metadata(package_root, protocol),
        "stage": f"synthetic-{stage}",
        "status": gate["status"],
        "seed_start": seeds[0],
        "seed_end": seeds[-1],
        "seed_count": len(seeds),
        "gate": gate,
        "records": {
            "stable": [item.payload() for item in stable],
            "locked": [item.payload() for item in locked],
            "near_critical": [item.payload() for item in near],
        },
        "classifier_tuning_permitted": False,
        "holdout_isolation": stage == "holdout",
    }
    path = CALIBRATION_PATH if stage == "calibration" else HOLDOUT_PATH
    artifact = _write(store, path, payload)
    return {
        "status": gate["status"],
        "stage": stage,
        "relative_path": artifact.relative_path,
        "sha256": artifact.sha256,
        "content_digest": artifact.content_digest,
        "gate": gate,
    }


def _operational_metrics(
    run: MechanismRun, terminal_start: int = 3001, terminal_stop: int = 4800
) -> dict[str, float]:
    selected = run.metrics[terminal_start - 1 : terminal_stop]
    observations = run.observations[terminal_start : terminal_stop + 1]
    if len(selected) != 1800 or len(observations) != 1800:
        raise ResearchGateError("GATE2B_NONFINITE", "Layer M terminal window")

    def imbalance(left: float, right: float) -> float:
        return abs(left - right) / max(left + right, 1e-12)

    values: dict[str, tuple[float, ...]] = {
        "acceptance_imbalance": tuple(
            imbalance(item.accepted_a, item.accepted_b) for item in selected
        ),
        "wait_imbalance": tuple(
            imbalance(item.wait_a, item.wait_b) for item in selected
        ),
        "courier_density_imbalance": tuple(abs(item[0]) for item in observations),
        "merchant_utilization_imbalance": tuple(
            imbalance(item.utilization_a, item.utilization_b) for item in selected
        ),
        "served_demand_imbalance": tuple(
            imbalance(item.served_a, item.served_b) for item in selected
        ),
        "service_inequality": tuple(item.service_inequality for item in selected),
        "accepted_orders": tuple(
            item.accepted_a + item.accepted_b for item in selected
        ),
        "served_demand": tuple(item.served_a + item.served_b for item in selected),
        "waiting_time": tuple((item.wait_a + item.wait_b) / 2.0 for item in selected),
    }
    sla_a = fmean(1.0 if item.wait_a > 12.0 else 0.0 for item in selected)
    sla_b = fmean(1.0 if item.wait_b > 12.0 else 0.0 for item in selected)
    result = {name: fmean(items) for name, items in values.items()}
    result.update(
        {
            "sla_12_minute_violation_rate_a": sla_a,
            "sla_12_minute_violation_rate_b": sla_b,
            "sla_12_minute_violation_rate_difference": abs(sla_a - sla_b),
            "served_sign": fmean(item.served_a - item.served_b for item in selected),
            "prep_time_imbalance_identifiable": 0.0,
        }
    )
    return result


def _simulate_model_run(
    layer: str,
    model: ReducedModel | DeliveryMechanism,
    *,
    alpha: float,
    multiplier: float,
    seed: int,
    initial_id: str,
    initial: Vector,
    horizon: int,
    noise_sd: float,
    weights: Vector,
) -> ClassifiedRun:
    if layer == "R":
        trajectory = cast(ReducedModel, model).simulate(
            initial,
            alpha,
            horizon,
            seed,
            noise_sd,
            magnitude=max(abs(value) for value in initial),
            direction_id=initial_id,
        )
        states = trajectory.states
        operational: dict[str, float] = {}
    else:
        run = cast(DeliveryMechanism, model).simulate(
            initial, alpha, horizon, seed, noise_sd
        )
        states = run.observations
        operational = _operational_metrics(run)
    return classify_states(
        layer,
        alpha,
        multiplier,
        seed,
        initial_id,
        states,
        weights,
        operational,
    )


def _sweep_layer(
    layer: str,
    model: ReducedModel | DeliveryMechanism,
    *,
    frozen_alpha: float,
    multipliers: tuple[float, ...],
    seeds: tuple[int, ...],
    horizon: int,
    noise_sd: float,
    weights: Vector,
) -> tuple[tuple[ClassifiedRun, ...], tuple[AlphaRegime, ...]]:
    records: list[ClassifiedRun] = []
    regimes: list[AlphaRegime] = []
    for multiplier in multipliers:
        alpha = frozen_alpha * multiplier
        selected: list[ClassifiedRun] = []
        for seed in seeds:
            for initial_id, initial in INITIALS:
                item = _simulate_model_run(
                    layer,
                    model,
                    alpha=alpha,
                    multiplier=multiplier,
                    seed=seed,
                    initial_id=initial_id,
                    initial=initial,
                    horizon=horizon,
                    noise_sd=noise_sd,
                    weights=weights,
                )
                selected.append(item)
                records.append(item)
        regimes.append(aggregate_alpha(tuple(selected)))
    return tuple(records), tuple(regimes)


def _model_context(
    protocol: Gate2bProtocol, preregistration: Preregistration
) -> tuple[
    tuple[int, ...],
    int,
    Vector,
    tuple[float, ...],
    ReducedModel,
    DeliveryMechanism,
    float,
    float,
]:
    trajectory = protocol.section("trajectory_protocol")
    seeds = _range(
        _mapping(trajectory.get("confirmatory_seeds"), "confirmatory_seeds"),
        "confirmatory_seeds",
    )
    horizon = _integer(trajectory.get("horizon"), "horizon")
    weights = _vector(trajectory.get("projection_weights_l1_normalized"), "weights")
    sweep = protocol.section("sweep")
    multipliers = tuple(
        _number(item, "coarse_multipliers")
        for item in _list(sweep.get("coarse_multipliers"), "coarse_multipliers")
    )
    layer_r_config = _mapping(preregistration.payload.get("layer_r"), "layer_r")
    layer_m_config = _mapping(preregistration.payload.get("layer_m"), "layer_m")
    identification = _mapping(
        preregistration.payload.get("identification"), "identification"
    )
    return (
        seeds,
        horizon,
        weights,
        multipliers,
        ReducedModel.from_config(layer_r_config),
        DeliveryMechanism.from_config(layer_m_config),
        _number(identification.get("layer_r_noise_sd"), "layer_r_noise_sd"),
        _number(identification.get("layer_m_noise_sd"), "layer_m_noise_sd"),
    )


def _frozen_layer(
    protocol: Gate2bProtocol, layer: str
) -> tuple[float, tuple[float, float]]:
    frozen = protocol.section("frozen_inputs")
    row = _mapping(frozen.get("layer_r" if layer == "R" else "layer_m"), layer)
    interval = _list(row.get("identification_interval_95"), "identification_interval")
    if len(interval) != 2:
        raise ResearchGateError("GATE2B_FROZEN_INPUT_MISMATCH", "interval")
    return _number(row.get("predicted_alpha_c"), "predicted_alpha_c"), (
        _number(interval[0], "interval.lower"),
        _number(interval[1], "interval.upper"),
    )


def _layer_path(layer: str, stage: str) -> str:
    return f"{GATE_ROOT}/layer_{layer.lower()}/{stage}/results.json"


def run_gate2b_coarse(
    package_root: Path,
    preregistration: Preregistration,
    store: ArtifactStore,
) -> dict[str, object]:
    protocol = load_gate2b_protocol(package_root)
    _verify_external_frozen(protocol, store)
    implementation = _implementation_digest(package_root)
    calibration, calibration_artifact = _require_stage_pass(
        store, CALIBRATION_PATH, implementation
    )
    holdout, holdout_artifact = _require_stage_pass(store, HOLDOUT_PATH, implementation)
    context = _model_context(protocol, preregistration)
    seeds, horizon, weights, multipliers, model_r, model_m, noise_r, noise_m = context
    outputs: dict[str, object] = {}
    for layer, model, noise in (("R", model_r, noise_r), ("M", model_m, noise_m)):
        frozen_alpha, interval = _frozen_layer(protocol, layer)
        records, regimes = _sweep_layer(
            layer,
            model,
            frozen_alpha=frozen_alpha,
            multipliers=multipliers,
            seeds=seeds,
            horizon=horizon,
            noise_sd=noise,
            weights=weights,
        )
        invalid = sum(item.label == "INVALID" for item in records)
        payload = {
            **_metadata(package_root, protocol),
            "stage": "coarse",
            "status": "PASS" if invalid == 0 else "FAIL",
            "layer": layer,
            "frozen_alpha": frozen_alpha,
            "identification_interval": interval,
            "calibration_sha256": calibration_artifact.sha256,
            "holdout_sha256": holdout_artifact.sha256,
            "calibration_status": calibration["status"],
            "holdout_status": holdout["status"],
            "seed_count": len(seeds),
            "horizon": horizon,
            "multipliers": multipliers,
            "invalid_count": invalid,
            "records": [item.payload() for item in records],
            "regimes": [item.payload() for item in regimes],
        }
        artifact = _write(store, _layer_path(layer, "coarse"), payload)
        outputs[layer] = {
            "status": payload["status"],
            "relative_path": artifact.relative_path,
            "sha256": artifact.sha256,
            "content_digest": artifact.content_digest,
            "regimes": [item.payload() for item in regimes],
        }
    status = (
        "PASS"
        if all(
            isinstance(value, dict) and value.get("status") == "PASS"
            for value in outputs.values()
        )
        else "FAIL"
    )
    return {"status": status, "stage": "coarse", "layers": outputs}


def _stats_from_payload(value: object) -> EquilibriumStatistics:
    row = _mapping(value, "statistics")
    coordinate = _list(row.get("coordinate_means"), "coordinate_means")
    blocks = _list(row.get("block_means"), "block_means")
    return EquilibriumStatistics(
        cast(Vector, tuple(_number(item, "coordinate_mean") for item in coordinate)),
        _number(row.get("projection_mean"), "projection_mean"),
        _number(row.get("covariance_trace"), "covariance_trace"),
        _number(row.get("cumulative_drift"), "cumulative_drift"),
        tuple(_number(item, "block_mean") for item in blocks),
        _number(row.get("block_mean_span"), "block_mean_span"),
        _number(row.get("positive_material_occupancy"), "positive occupancy"),
        _number(row.get("negative_material_occupancy"), "negative occupancy"),
        _number(row.get("material_sign_occupancy"), "material occupancy"),
    )


def _record_from_payload(value: object) -> ClassifiedRun:
    row = _mapping(value, "record")
    operational = _mapping(row.get("operational"), "operational")
    label = str(row.get("label"))
    if label == "INVALID":
        nan = float("nan")
        final_state: Vector = (nan, nan, nan)
        stats = EquilibriumStatistics(
            (nan, nan, nan), nan, nan, nan, (), nan, nan, nan, nan
        )
    else:
        final_state = _vector(row.get("final_state"), "final_state")
        stats = _stats_from_payload(row.get("statistics"))
    return ClassifiedRun(
        str(row.get("layer")),
        _number(row.get("alpha"), "alpha"),
        _number(row.get("multiplier"), "multiplier"),
        _integer(row.get("seed"), "seed"),
        str(row.get("initial_id")),
        final_state,
        stats,
        label,
        str(row.get("trace_digest")),
        {
            str(key): _number(item, f"operational.{key}")
            for key, item in operational.items()
        },
    )


def _records_from_stage(payload: dict[str, object]) -> tuple[ClassifiedRun, ...]:
    return tuple(
        _record_from_payload(item) for item in _list(payload.get("records"), "records")
    )


def run_gate2b_fine(
    package_root: Path,
    preregistration: Preregistration,
    store: ArtifactStore,
) -> dict[str, object]:
    protocol = load_gate2b_protocol(package_root)
    implementation = _implementation_digest(package_root)
    _require_stage_pass(store, HOLDOUT_PATH, implementation)
    context = _model_context(protocol, preregistration)
    seeds, horizon, weights, _, model_r, model_m, noise_r, noise_m = context
    subdivisions = _integer(
        protocol.section("sweep").get("fine_interval_subdivisions"),
        "fine_interval_subdivisions",
    )
    outputs: dict[str, object] = {}
    for layer, model, noise in (("R", model_r, noise_r), ("M", model_m, noise_m)):
        coarse, coarse_artifact = _read(store, _layer_path(layer, "coarse"))
        _same_implementation(coarse, implementation, f"{layer} coarse")
        if coarse.get("status") == "PASS":
            coarse_records = _records_from_stage(coarse)
            coarse_regimes = tuple(
                aggregate_alpha(
                    tuple(item for item in coarse_records if item.alpha == alpha)
                )
                for alpha in sorted({item.alpha for item in coarse_records})
            )
            bracket = select_coarse_bracket(coarse_regimes)
        else:
            bracket = None
        frozen_alpha, interval = _frozen_layer(protocol, layer)
        reason_codes: tuple[str, ...]
        if bracket is None:
            records: tuple[ClassifiedRun, ...] = ()
            regimes: tuple[AlphaRegime, ...] = ()
            multipliers: tuple[float, ...] = ()
            status = "FAIL"
            reason_codes = ("GATE2B_NO_TRANSITION",)
            bracket_payload: tuple[float, float] | None = None
        else:
            lower, upper = bracket
            step = (upper.multiplier - lower.multiplier) / subdivisions
            multipliers = tuple(
                lower.multiplier + step * index for index in range(1, subdivisions)
            )
            records, regimes = _sweep_layer(
                layer,
                model,
                frozen_alpha=frozen_alpha,
                multipliers=multipliers,
                seeds=seeds,
                horizon=horizon,
                noise_sd=noise,
                weights=weights,
            )
            status = (
                "PASS" if all(item.label != "INVALID" for item in records) else "FAIL"
            )
            reason_codes = () if status == "PASS" else ("GATE2B_NONFINITE",)
            bracket_payload = (lower.multiplier, upper.multiplier)
        payload = {
            **_metadata(package_root, protocol),
            "stage": "fine",
            "status": status,
            "layer": layer,
            "frozen_alpha": frozen_alpha,
            "identification_interval": interval,
            "coarse_sha256": coarse_artifact.sha256,
            "selected_coarse_multiplier_bracket": bracket_payload,
            "subdivisions": subdivisions,
            "multipliers": multipliers,
            "reason_codes": reason_codes,
            "records": [item.payload() for item in records],
            "regimes": [item.payload() for item in regimes],
        }
        artifact = _write(store, _layer_path(layer, "fine"), payload)
        outputs[layer] = {
            "status": status,
            "relative_path": artifact.relative_path,
            "sha256": artifact.sha256,
            "content_digest": artifact.content_digest,
            "selected_coarse_multiplier_bracket": bracket_payload,
            "multipliers": multipliers,
            "reason_codes": reason_codes,
        }
    status = (
        "PASS"
        if all(
            isinstance(value, dict) and value.get("status") == "PASS"
            for value in outputs.values()
        )
        else "FAIL"
    )
    return {"status": status, "stage": "fine", "layers": outputs}


def _same_implementation(
    payload: dict[str, object], implementation_digest: str, stage: str
) -> None:
    if payload.get("implementation_digest") != implementation_digest:
        raise ResearchGateError(
            "GATE2B_CONFIRMATORY_CONTAMINATION", f"{stage} implementation changed"
        )


def _find_multiplier(
    regimes: tuple[AlphaRegime, ...], multiplier: float
) -> AlphaRegime | None:
    return next(
        (item for item in regimes if abs(item.multiplier - multiplier) <= 1e-12),
        None,
    )


def _bootstrap_regime(
    regime: AlphaRegime, sampled_seeds: tuple[int, ...]
) -> AlphaRegime:
    labels = dict(regime.pair_labels_by_seed)
    selected = tuple(labels.get(seed, "INVALID") for seed in sampled_seeds)
    restored = sum(label == "PAIRED_RESTORED" for label in selected)
    locked = sum(label == "PAIRED_LOCKED" for label in selected)
    invalid = sum(label == "INVALID" for label in selected)
    transitional = len(selected) - restored - locked - invalid
    wr = wilson_interval(restored, len(selected))
    wl = wilson_interval(locked, len(selected))
    if restored >= 48 and wr[0] > 0.60:
        label = "ROBUST_RESTORED"
    elif locked >= 48 and wl[0] > 0.60:
        label = "ROBUST_LOCKED"
    else:
        label = "TRANSITIONAL"
    return AlphaRegime(
        regime.alpha,
        regime.multiplier,
        label,
        restored,
        locked,
        transitional,
        invalid,
        regime.zero_restored_count,
        wr,
        wl,
        regime.zero_restored_wilson95,
        regime.pair_labels_by_seed,
    )


def _transition_bootstrap(
    regimes: tuple[AlphaRegime, ...], *, seed: int, samples: int = 1000
) -> dict[str, object]:
    if not regimes:
        return {"valid_fraction": 0.0, "valid_count": 0, "samples": samples}
    seed_ids = tuple(seed for seed, _ in regimes[0].pair_labels_by_seed)
    if len(seed_ids) != 64:
        return {"valid_fraction": 0.0, "valid_count": 0, "samples": samples}
    rng = random.Random(seed)
    midpoints: list[float] = []
    widths: list[float] = []
    for _ in range(samples):
        selected = tuple(seed_ids[rng.randrange(len(seed_ids))] for _ in seed_ids)
        resampled = tuple(_bootstrap_regime(item, selected) for item in regimes)
        bracket = observed_transition(resampled)
        if bracket is not None:
            midpoints.append((bracket[0] + bracket[1]) / 2.0)
            widths.append(bracket[1] - bracket[0])
    return {
        "samples": samples,
        "valid_count": len(midpoints),
        "invalid_count": samples - len(midpoints),
        "valid_fraction": len(midpoints) / samples,
        "midpoint_interval95": percentile_interval(tuple(midpoints))
        if midpoints
        else None,
        "width_interval95": percentile_interval(tuple(widths)) if widths else None,
    }


def _paired_bootstrap_interval(
    differences: tuple[float, ...], *, seed: int, samples: int = 1000
) -> tuple[float, float]:
    if not differences:
        return (0.0, 0.0)
    rng = random.Random(seed)
    estimates = tuple(
        fmean(differences[rng.randrange(len(differences))] for _ in differences)
        for _ in range(samples)
    )
    return percentile_interval(estimates)


def _operational_correspondence(
    records: tuple[ClassifiedRun, ...],
    bracket: tuple[float, float] | None,
) -> dict[str, object]:
    if bracket is None:
        return {
            "status": "FAIL",
            "reason_code": "GATE2B_OPERATIONAL_MISMATCH",
            "prep_time_imbalance": "NOT_IDENTIFIABLE_NO_PROXY",
        }
    lower_alpha, upper_alpha = bracket
    lower = {
        (item.seed, item.initial_id): item
        for item in records
        if abs(item.alpha - lower_alpha) <= 1e-12
        and item.initial_id in {"positive", "negative"}
    }
    upper = {
        (item.seed, item.initial_id): item
        for item in records
        if abs(item.alpha - upper_alpha) <= 1e-12
        and item.initial_id in {"positive", "negative"}
    }
    seeds = tuple(sorted({seed for seed, _ in lower} & {seed for seed, _ in upper}))
    metrics = (
        "service_inequality",
        "acceptance_imbalance",
        "wait_imbalance",
        "sla_12_minute_violation_rate_difference",
        "courier_density_imbalance",
        "merchant_utilization_imbalance",
        "served_demand_imbalance",
    )
    contrasts: dict[str, object] = {}
    positive_support = 0
    primary_pass = False
    for offset, metric in enumerate(metrics):
        differences: list[float] = []
        for seed in seeds:
            key_positive = (seed, "positive")
            key_negative = (seed, "negative")
            required = (
                lower.get(key_positive),
                lower.get(key_negative),
                upper.get(key_positive),
                upper.get(key_negative),
            )
            if any(item is None or metric not in item.operational for item in required):
                continue
            low_positive, low_negative, high_positive, high_negative = cast(
                tuple[ClassifiedRun, ClassifiedRun, ClassifiedRun, ClassifiedRun],
                required,
            )
            low_value = fmean(
                (
                    low_positive.operational[metric],
                    low_negative.operational[metric],
                )
            )
            high_value = fmean(
                (
                    high_positive.operational[metric],
                    high_negative.operational[metric],
                )
            )
            differences.append(high_value - low_value)
        values = tuple(differences)
        mean_difference = fmean(values) if values else 0.0
        interval = _paired_bootstrap_interval(values, seed=74000 + offset, samples=1000)
        metric_pass = mean_difference > 0.0 and interval[0] > 0.0
        contrasts[metric] = {
            "pair_count": len(values),
            "mean_upper_minus_lower": mean_difference,
            "paired_bootstrap_interval95": interval,
            "positive_contrast": metric_pass,
        }
        if metric == "service_inequality":
            primary_pass = mean_difference >= 0.005 and interval[0] > 0.0
        elif metric_pass:
            positive_support += 1
    sign_count = 0
    for seed in seeds:
        positive = upper.get((seed, "positive"))
        negative = upper.get((seed, "negative"))
        if positive is None or negative is None:
            continue
        if (
            positive.label == negative.label == "LOCKED"
            and positive.operational.get("served_sign", 0.0)
            * positive.statistics.projection_mean
            > 0.0
            and negative.operational.get("served_sign", 0.0)
            * negative.statistics.projection_mean
            > 0.0
        ):
            sign_count += 1
    sign_interval = wilson_interval(sign_count, 64)
    sign_pass = sign_count >= 48 and sign_interval[0] > 0.60
    passed = len(seeds) == 64 and primary_pass and sign_pass and positive_support >= 2
    return {
        "status": "PASS" if passed else "FAIL",
        "lower_alpha": lower_alpha,
        "upper_alpha": upper_alpha,
        "seed_count": len(seeds),
        "primary_service_inequality_pass": primary_pass,
        "projection_to_served_sign_count": sign_count,
        "projection_to_served_sign_wilson95": sign_interval,
        "projection_to_served_sign_pass": sign_pass,
        "supporting_positive_contrast_count": positive_support,
        "supporting_positive_contrast_required": 2,
        "contrasts": contrasts,
        "prep_time_imbalance": "NOT_IDENTIFIABLE_NO_PROXY",
    }


def _layer_assessment(
    protocol: Gate2bProtocol,
    layer: str,
    records: tuple[ClassifiedRun, ...],
) -> dict[str, object]:
    regimes = tuple(
        aggregate_alpha(tuple(item for item in records if item.alpha == alpha))
        for alpha in sorted({item.alpha for item in records})
    )
    frozen_alpha, identification_interval = _frozen_layer(protocol, layer)
    reasons: list[str] = []
    alpha_zero = _find_multiplier(regimes, 0.0)
    alpha_zero_pass = bool(
        alpha_zero is not None
        and alpha_zero.zero_restored_count >= 58
        and alpha_zero.zero_restored_wilson95[0] > 0.80
    )
    if not alpha_zero_pass:
        reasons.append("GATE2B_NEGATIVE_CONTROL_FAILED")
    weak_rows = tuple(_find_multiplier(regimes, value) for value in (0.40, 0.65))
    weak_pass = all(
        item is not None and item.label == "ROBUST_RESTORED" for item in weak_rows
    )
    if not weak_pass:
        reasons.append("GATE2B_WEAK_CONTROL_FAILED")
    strong_rows = tuple(_find_multiplier(regimes, value) for value in (1.40, 1.60))
    strong_pass = all(
        item is not None
        and item.label == "ROBUST_LOCKED"
        and item.paired_locked_count >= 48
        and item.locked_wilson95[0] > 0.60
        for item in strong_rows
    )
    if not strong_pass:
        reasons.extend(
            ("GATE2B_STRONG_CONTROL_FAILED", "GATE2B_PATH_DEPENDENCE_FAILED")
        )
    bracket = observed_transition(regimes)
    observed_alpha: float | None = None
    absolute_error: float | None = None
    relative_error: float | None = None
    width: float | None = None
    relative_width: float | None = None
    interval_overlap: bool | None = None
    if bracket is None:
        reasons.append("GATE2B_NO_TRANSITION")
    else:
        observed_alpha = (bracket[0] + bracket[1]) / 2.0
        width = bracket[1] - bracket[0]
        absolute_error = abs(observed_alpha - frozen_alpha)
        relative_error = absolute_error / abs(observed_alpha)
        relative_width = width / abs(observed_alpha)
        interval_overlap = (
            identification_interval[0] <= bracket[1]
            and bracket[0] <= identification_interval[1]
        )
        if relative_error > 0.01:
            reasons.append("GATE2B_THRESHOLD_MISS")
        if relative_width > 0.025:
            reasons.append("GATE2B_TRANSITION_TOO_WIDE")
    bootstrap_seed = 73000 if layer == "R" else 74000
    bootstrap = _transition_bootstrap(regimes, seed=bootstrap_seed)
    if _number(bootstrap.get("valid_fraction"), "bootstrap.valid_fraction") < 0.95:
        reasons.append("GATE2B_INCONCLUSIVE")
    fatal = any(
        reason not in {"GATE2B_THRESHOLD_MISS", "GATE2B_TRANSITION_TOO_WIDE"}
        for reason in reasons
    )
    if fatal or relative_error is None or relative_width is None:
        status = "FAIL"
    elif relative_error <= 0.01 and relative_width <= 0.025:
        status = "PASS"
    elif relative_error <= 0.02 and relative_width <= 0.05:
        status = "PARTIAL"
    else:
        status = "FAIL"
    return {
        "layer": layer,
        "status": status,
        "frozen_alpha": frozen_alpha,
        "frozen_identification_interval95": identification_interval,
        "observed_transition_interval": bracket,
        "observed_alpha": observed_alpha,
        "absolute_prediction_error": absolute_error,
        "relative_prediction_error": relative_error,
        "transition_width": width,
        "relative_transition_width": relative_width,
        "identification_interval_intersects_bracket": interval_overlap,
        "identification_interval_overlap_role": (
            "SUPPLEMENTARY_CORRESPONDENCE_DIAGNOSTIC_ONLY"
        ),
        "alpha_zero_restored_count": alpha_zero.zero_restored_count
        if alpha_zero
        else 0,
        "alpha_zero_restored_wilson95": alpha_zero.zero_restored_wilson95
        if alpha_zero
        else (0.0, 0.0),
        "alpha_zero_pass": alpha_zero_pass,
        "weak_controls_pass": weak_pass,
        "strong_controls_pass": strong_pass,
        "path_dependence_pass": strong_pass,
        "transition_bootstrap": bootstrap,
        "reason_codes": tuple(dict.fromkeys(reasons)),
        "regimes": [item.payload() for item in regimes],
    }


def _replay(
    protocol: Gate2bProtocol,
    preregistration: Preregistration,
    package_root: Path,
    store: ArtifactStore,
    records_by_layer: dict[str, tuple[ClassifiedRun, ...]],
) -> tuple[dict[str, object], StoredArtifact]:
    context = _model_context(protocol, preregistration)
    _, horizon, weights, _, model_r, model_m, noise_r, noise_m = context
    rows: list[dict[str, object]] = []
    all_pass = True
    for layer, model, noise in (("R", model_r, noise_r), ("M", model_m, noise_m)):
        selected = {
            (item.alpha, item.seed, item.initial_id): item
            for item in records_by_layer[layer]
            if item.seed in REPLAY_SEEDS
        }
        for (alpha, seed, initial_id), expected in sorted(selected.items()):
            initial = dict(INITIALS)[initial_id]
            observed = _simulate_model_run(
                layer,
                model,
                alpha=alpha,
                multiplier=expected.multiplier,
                seed=seed,
                initial_id=initial_id,
                initial=initial,
                horizon=horizon,
                noise_sd=noise,
                weights=weights,
            )
            passed = (
                observed.trace_digest == expected.trace_digest
                and observed.label == expected.label
                and observed.statistics == expected.statistics
                and observed.operational == expected.operational
            )
            all_pass = all_pass and passed
            rows.append(
                {
                    "layer": layer,
                    "alpha": alpha,
                    "multiplier": expected.multiplier,
                    "seed": seed,
                    "initial_id": initial_id,
                    "expected_trace_digest": expected.trace_digest,
                    "observed_trace_digest": observed.trace_digest,
                    "pass": passed,
                }
            )
    payload = {
        **_metadata(package_root, protocol),
        "stage": "replay",
        "status": "PASS" if all_pass else "FAIL",
        "required_seeds": REPLAY_SEEDS,
        "check_count": len(rows),
        "failed_count": sum(not bool(item["pass"]) for item in rows),
        "checks": rows,
    }
    artifact = _write(store, REPLAY_PATH, payload)
    return payload, artifact


def _early_failure_summary(
    protocol: Gate2bProtocol,
    package_root: Path,
    store: ArtifactStore,
    *,
    failed_stage: str,
    source: dict[str, object],
    source_artifact: StoredArtifact,
) -> dict[str, object]:
    payload = {
        **_metadata(package_root, protocol),
        "stage": "gate2b-validation",
        "status": "FAIL",
        "original_gate2": "FAIL_UNCHANGED",
        "classifier_calibration": "PASS"
        if failed_stage == "synthetic-holdout"
        else "FAIL",
        "classifier_holdout": "FAIL"
        if failed_stage == "synthetic-holdout"
        else "NOT_EXECUTED",
        "failed_stage": failed_stage,
        "reason_codes": ("GATE2B_CLASSIFIER_CALIBRATION_FAILED",),
        "source_artifact": {
            "relative_path": source_artifact.relative_path,
            "sha256": source_artifact.sha256,
            "content_digest": source_artifact.content_digest,
            "status": source.get("status"),
        },
        "layers": {},
        "gate3_eligibility": "NO",
        "gate3_executed": False,
        "research_line_status": "NO-GO",
        "claim_limit": "No novelty or external-validity claim",
    }
    artifact = _write(store, VALIDATION_PATH, payload)
    return {
        "status": "FAIL",
        "gate3_eligibility": "NO",
        "relative_path": artifact.relative_path,
        "sha256": artifact.sha256,
        "content_digest": artifact.content_digest,
        "reason_codes": payload["reason_codes"],
    }


def finalize_gate2b(
    package_root: Path,
    preregistration: Preregistration,
    store: ArtifactStore,
) -> dict[str, object]:
    protocol = load_gate2b_protocol(package_root)
    implementation = _implementation_digest(package_root)
    calibration, calibration_artifact = _read(store, CALIBRATION_PATH)
    _same_implementation(calibration, implementation, "calibration")
    if calibration.get("status") != "PASS":
        return _early_failure_summary(
            protocol,
            package_root,
            store,
            failed_stage="synthetic-calibration",
            source=calibration,
            source_artifact=calibration_artifact,
        )
    holdout, holdout_artifact = _read(store, HOLDOUT_PATH)
    _same_implementation(holdout, implementation, "holdout")
    if holdout.get("status") != "PASS":
        return _early_failure_summary(
            protocol,
            package_root,
            store,
            failed_stage="synthetic-holdout",
            source=holdout,
            source_artifact=holdout_artifact,
        )
    records_by_layer: dict[str, tuple[ClassifiedRun, ...]] = {}
    stage_failures: dict[str, tuple[str, ...]] = {}
    stage_artifacts: list[StoredArtifact] = [calibration_artifact, holdout_artifact]
    for layer in ("R", "M"):
        coarse, coarse_artifact = _read(store, _layer_path(layer, "coarse"))
        fine, fine_artifact = _read(store, _layer_path(layer, "fine"))
        _same_implementation(coarse, implementation, f"{layer} coarse")
        _same_implementation(fine, implementation, f"{layer} fine")
        records_by_layer[layer] = _records_from_stage(coarse) + _records_from_stage(
            fine
        )
        failure_reasons: list[str] = []
        if coarse.get("status") != "PASS":
            failure_reasons.append("GATE2B_NONFINITE")
        if fine.get("status") != "PASS":
            failure_reasons.extend(
                str(item)
                for item in _list(fine.get("reason_codes"), "fine.reason_codes")
            )
        stage_failures[layer] = tuple(dict.fromkeys(failure_reasons))
        stage_artifacts.extend((coarse_artifact, fine_artifact))
    replay, replay_artifact = _replay(
        protocol, preregistration, package_root, store, records_by_layer
    )
    stage_artifacts.append(replay_artifact)
    assessment_r = _layer_assessment(protocol, "R", records_by_layer["R"])
    assessment_m = _layer_assessment(protocol, "M", records_by_layer["M"])
    for layer, assessment in (("R", assessment_r), ("M", assessment_m)):
        if stage_failures[layer]:
            assessment["status"] = "FAIL"
            assessment["reason_codes"] = tuple(
                dict.fromkeys(
                    cast(tuple[str, ...], assessment["reason_codes"])
                    + stage_failures[layer]
                )
            )
    bracket_m = assessment_m.get("observed_transition_interval")
    operational = _operational_correspondence(
        records_by_layer["M"],
        cast(tuple[float, float] | None, bracket_m),
    )
    reasons: list[str] = []
    reasons.extend(cast(tuple[str, ...], assessment_r["reason_codes"]))
    reasons.extend(cast(tuple[str, ...], assessment_m["reason_codes"]))
    if assessment_r["status"] == "FAIL":
        reasons.append("GATE2B_LAYER_R_FAILED")
    if assessment_m["status"] == "FAIL":
        reasons.append("GATE2B_LAYER_M_FAILED")
    if operational["status"] != "PASS":
        reasons.append("GATE2B_OPERATIONAL_MISMATCH")
    if replay["status"] != "PASS":
        reasons.append("GATE2B_REPLAY_FAILED")
    layer_statuses = (str(assessment_r["status"]), str(assessment_m["status"]))
    if (
        layer_statuses == ("PASS", "PASS")
        and operational["status"] == "PASS"
        and replay["status"] == "PASS"
    ):
        status = "PASS"
    elif (
        all(item in {"PASS", "PARTIAL"} for item in layer_statuses)
        and "PARTIAL" in layer_statuses
        and operational["status"] == "PASS"
        and replay["status"] == "PASS"
    ):
        status = "PARTIAL"
    else:
        status = "FAIL"
    gate3 = (
        "YES" if status == "PASS" else "CONDITIONAL" if status == "PARTIAL" else "NO"
    )
    payload = {
        **_metadata(package_root, protocol),
        "stage": "gate2b-validation",
        "status": status,
        "original_gate2": "FAIL_UNCHANGED",
        "classifier_calibration": "PASS",
        "classifier_holdout": "PASS",
        "layers": {"R": assessment_r, "M": assessment_m},
        "operational_correspondence": operational,
        "replay": {
            "status": replay["status"],
            "relative_path": replay_artifact.relative_path,
            "sha256": replay_artifact.sha256,
            "content_digest": replay_artifact.content_digest,
        },
        "reason_codes": tuple(dict.fromkeys(reasons)),
        "bulk_artifacts": [
            {
                "relative_path": item.relative_path,
                "sha256": item.sha256,
                "content_digest": item.content_digest,
            }
            for item in stage_artifacts
        ],
        "gate3_eligibility": gate3,
        "gate3_executed": False,
        "research_line_status": "GO"
        if status == "PASS"
        else "CONDITIONAL GO"
        if status == "PARTIAL"
        else "NO-GO",
        "claim_limit": "No novelty or external-validity claim; Gate 3 not executed",
    }
    artifact = _write(store, VALIDATION_PATH, payload)
    return {
        "status": status,
        "gate3_eligibility": gate3,
        "relative_path": artifact.relative_path,
        "sha256": artifact.sha256,
        "content_digest": artifact.content_digest,
        "layers": payload["layers"],
        "operational_correspondence": operational,
        "reason_codes": payload["reason_codes"],
    }
