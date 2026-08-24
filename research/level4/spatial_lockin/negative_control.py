from __future__ import annotations

import hashlib
import platform
import random
import subprocess
from collections import Counter
from dataclasses import replace
from datetime import UTC, datetime
from math import isfinite, sqrt
from pathlib import Path
from statistics import fmean
from typing import cast

from .artifacts import ArtifactStore, StoredArtifact
from .diagnostic_statistics import (
    autocorrelation,
    block_averaged_slope,
    correlation,
    covariance_matrix,
    diagonal_matrix,
    distribution,
    matrix_eigenvalues,
    mean_first_difference,
    moving_block_difference_interval,
    moving_block_slope_interval,
    ols_slope,
    quantile,
    relative_matrix_error,
    solve_discrete_lyapunov,
    theil_sen_slope,
)
from .gate2 import (
    RunSummary,
    _classify,
    _summary_from_states,
    _wilson,
    verify_frozen_inputs,
)
from .linalg import Matrix, Vector, dot, matvec
from .mechanism import DeliveryMechanism, MechanismState
from .preregistration import Preregistration, canonical_json
from .reason_codes import ResearchGateError
from .reduced_model import ReducedModel

PROTOCOL_ID = "negative-control-diagnostic-v1"
PREREGISTRATION_REPORT = "NEGATIVE_CONTROL_DIAGNOSTIC_PREREGISTRATION.md"
PREREGISTRATION_SHA256 = (
    "0db5478439e28aa979b5eb845d2ad65abc49e2add096c4f94797cbb9f5c9bfc9"
)
GATE2_REPORT_SHA256 = "4a184998e15c02c9e9a54bbb681b0d1d0dbbf6a17b5eed81c24c614a1d9a1a97"
GATE2_REPOSITORY_SUMMARY_SHA256 = (
    "6a56279dae504dc01bf3d8109c74a5aecc7d70af5ab19bede8b360be9d77b72f"
)
GATE2_EXTERNAL_SUMMARY_SHA256 = (
    "c81c3d67d8834abab58344b022e39a9e2d7b3a6aa429f63404f9a214cb1953c5"
)
R_COARSE_SHA256 = "88ed2b1e34c035af4e8c9e1aebc38fa53502b7063d58028aa009ffc30648184d"
M_COARSE_SHA256 = "fc776837bbef79d5cef77c31b0b30acf8a14dbd30fabf741be50927cfd102b93"
DIAGNOSTIC_SEEDS = tuple(range(41000, 41064))
SYNTHETIC_SEEDS = tuple(range(42000, 42256))
REPLAY_SEEDS = (21000, 21001, 21002, 21003, 21031, 21063)
HORIZONS = (1200, 2400, 4800, 9600)
WINDOWS = (150, 300, 600, 1200)
PLACEMENTS = (0, 300, 600, 900)
INITIALS: tuple[tuple[str, Vector], ...] = (
    ("zero", (0.0, 0.0, 0.0)),
    ("positive_small", (0.001, 0.001, 0.001)),
    ("negative_small", (-0.001, -0.001, -0.001)),
)
EPSILON = 0.02
NOISE_SD = 0.00002


def _git(repository_root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _sha256(path: Path) -> str:
    if not path.is_file():
        raise ResearchGateError("DIAGNOSTIC_INPUT_MISMATCH", str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_repository_inputs(package_root: Path) -> dict[str, str]:
    reports = package_root / "reports"
    expected = {
        PREREGISTRATION_REPORT: PREREGISTRATION_SHA256,
        "GATE2_LONG_HORIZON_VALIDATION.md": GATE2_REPORT_SHA256,
        "GATE2_VALIDATION_SUMMARY.json": GATE2_REPOSITORY_SUMMARY_SHA256,
    }
    observed = {name: _sha256(reports / name) for name in expected}
    for name, digest in expected.items():
        if observed[name] != digest:
            raise ResearchGateError(
                "DIAGNOSTIC_INPUT_MISMATCH", f"{name} SHA-256 changed"
            )
    return observed


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ResearchGateError("DIAGNOSTIC_INPUT_MISMATCH", f"{name} is not numeric")
    result = float(value)
    if not isfinite(result):
        raise ResearchGateError("DIAGNOSTIC_NONFINITE", name)
    return result


def _numeric(value: object) -> float:
    return _number(value, "diagnostic value")


def _integer(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ResearchGateError("DIAGNOSTIC_INPUT_MISMATCH", "expected integer")
    return value


def _vector(value: object, name: str) -> Vector:
    if not isinstance(value, list) or len(value) != 3:
        raise ResearchGateError("DIAGNOSTIC_INPUT_MISMATCH", name)
    return cast(Vector, tuple(_number(item, name) for item in value))


def _record_from_payload(value: object) -> RunSummary:
    if not isinstance(value, dict):
        raise ResearchGateError("DIAGNOSTIC_INPUT_MISMATCH", "Gate 2 record")
    operational = value.get("operational")
    if not isinstance(operational, dict):
        raise ResearchGateError("DIAGNOSTIC_INPUT_MISMATCH", "operational metrics")
    typed_operational = {
        str(key): _number(item, f"operational.{key}")
        for key, item in operational.items()
    }
    seed = value.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ResearchGateError("DIAGNOSTIC_INPUT_MISMATCH", "seed")
    return RunSummary(
        str(value.get("layer")),
        _number(value.get("alpha"), "alpha"),
        seed,
        str(value.get("initial_id")),
        _vector(value.get("final_state"), "final_state"),
        _number(value.get("imbalance_mean"), "imbalance_mean"),
        _number(value.get("imbalance_median"), "imbalance_median"),
        _number(value.get("imbalance_variance"), "imbalance_variance"),
        _number(value.get("sign_persistence"), "sign_persistence"),
        _number(value.get("projection_mean"), "projection_mean"),
        _number(value.get("projection_final"), "projection_final"),
        _number(value.get("slope"), "slope"),
        _number(value.get("preceding_third_mean"), "preceding_third_mean"),
        _number(value.get("final_third_mean"), "final_third_mean"),
        str(value.get("trace_digest")),
        typed_operational,
        str(value.get("classification")),
    )


def classifier_components(
    summary: RunSummary, epsilon: float = EPSILON
) -> dict[str, object]:
    finite = all(
        isfinite(value)
        for value in (
            summary.imbalance_mean,
            summary.slope,
            summary.preceding_third_mean,
            summary.final_third_mean,
        )
    )
    magnitude = finite and summary.imbalance_mean <= epsilon
    slope = finite and summary.slope <= 0.0
    window = finite and summary.final_third_mean <= summary.preceding_third_mean
    return {
        "finite_pass": finite,
        "magnitude_pass": magnitude,
        "slope_pass": slope,
        "window_pass": window,
        "all_pass": finite and magnitude and slope and window,
        "frozen_classifier_label": _classify(summary, epsilon),
        "archived_record_label": summary.classification,
    }


def _load_archived_controls(
    store: ArtifactStore, layer: str
) -> tuple[tuple[RunSummary, ...], StoredArtifact]:
    filename = f"gate2_long_horizon/{layer.lower()}-coarse.json"
    digest = R_COARSE_SHA256 if layer == "R" else M_COARSE_SHA256
    payload, artifact = store.read_json(
        "confirmatory", filename, expected_sha256=digest
    )
    records = payload.get("records")
    if not isinstance(records, list):
        raise ResearchGateError("DIAGNOSTIC_INPUT_MISMATCH", f"{layer} records")
    controls = tuple(
        _record_from_payload(item)
        for item in records
        if isinstance(item, dict)
        and item.get("alpha") == 0.0
        and item.get("initial_id") == "zero"
    )
    if tuple(sorted(item.seed for item in controls)) != tuple(range(21000, 21064)):
        raise ResearchGateError("DIAGNOSTIC_INPUT_MISMATCH", f"{layer} controls")
    return controls, artifact


def _decomposition(records: tuple[RunSummary, ...]) -> dict[str, object]:
    rows = tuple(
        {
            "seed": item.seed,
            "imbalance_mean": item.imbalance_mean,
            "slope": item.slope,
            "preceding_third_mean": item.preceding_third_mean,
            "final_third_mean": item.final_third_mean,
            "growth_difference": item.final_third_mean - item.preceding_third_mean,
            "growth_relative": (item.final_third_mean - item.preceding_third_mean)
            / max(item.preceding_third_mean, 1e-15),
            "growth_standardized": (item.final_third_mean - item.preceding_third_mean)
            / max(sqrt(item.imbalance_variance), 1e-15),
            "growth_material": abs(item.final_third_mean - item.preceding_third_mean)
            > max(0.5 * sqrt(item.imbalance_variance), 0.10 * EPSILON),
            "components": classifier_components(item),
        }
        for item in records
    )
    keys = ("finite_pass", "magnitude_pass", "slope_pass", "window_pass", "all_pass")
    counts = {
        key: sum(bool(cast(dict[str, object], row["components"])[key]) for row in rows)
        for key in keys
    }
    growth = tuple(_numeric(row["growth_difference"]) for row in rows)
    return {
        "seed_count": len(records),
        "counts": counts,
        "slope_distribution": distribution(tuple(item.slope for item in records)),
        "growth_difference_distribution": distribution(growth),
        "material_growth_count": sum(bool(row["growth_material"]) for row in rows),
        "records": rows,
    }


def _projection_r(model: ReducedModel, states: tuple[Vector, ...]) -> tuple[float, ...]:
    return tuple(dot(model.c, state) for state in states)


def _projection_m(
    model: DeliveryMechanism, states: tuple[Vector, ...]
) -> tuple[float, ...]:
    raw_weights = model.parameters["service_score_weights"]
    if not isinstance(raw_weights, list):
        raise ResearchGateError("DIAGNOSTIC_INPUT_MISMATCH", "service weights")
    weights = tuple(float(item) for item in raw_weights)
    return tuple(
        sum(weight * value for weight, value in zip(weights, state, strict=True))
        for state in states
    )


def _magnitudes(states: tuple[Vector, ...]) -> tuple[float, ...]:
    return tuple(sqrt(dot(state, state)) for state in states)


def _window_record(
    layer: str,
    seed: int,
    initial_id: str,
    states: tuple[Vector, ...],
    projection: tuple[float, ...],
) -> dict[str, object]:
    summary = _summary_from_states(
        layer, 0.0, seed, initial_id, states, projection, {}, len(states)
    )
    classified = replace(summary, classification=_classify(summary, EPSILON))
    return {
        **classified.payload(),
        "components": classifier_components(classified),
    }


def _mechanism_reference(model: DeliveryMechanism, imbalance: Vector) -> Vector:
    p = model.parameters

    def number(name: str) -> float:
        return _number(p.get(name), f"layer_m.{name}")

    c0 = number("baseline_couriers")
    m0 = number("baseline_merchant_capacity")
    d0 = number("baseline_demand")
    base = number("base_acceptance")
    acceptance_delta = (
        number("supply_acceptance_weight") * imbalance[0]
        + number("merchant_acceptance_weight") * imbalance[1]
    )
    acceptance_a = max(0.05, min(0.98, base + acceptance_delta))
    acceptance_b = max(0.05, min(0.98, base - acceptance_delta))
    courier_a, courier_b = c0 * (1 + imbalance[0]), c0 * (1 - imbalance[0])
    merchant_a, merchant_b = m0 * (1 + imbalance[1]), m0 * (1 - imbalance[1])
    demand_a, demand_b = d0 * (1 + imbalance[2]), d0 * (1 - imbalance[2])
    served_a = min(demand_a * acceptance_a, merchant_a, 0.9 * courier_a)
    served_b = min(demand_b * acceptance_b, merchant_b, 0.9 * courier_b)
    opportunity_a, opportunity_b = served_a / courier_a, served_b / courier_b
    utilization_a, utilization_b = served_a / merchant_a, served_b / merchant_b
    baseline_opportunity = d0 * base / c0
    baseline_utilization = d0 * base / m0
    opportunity_imbalance = (opportunity_a - opportunity_b) / (2 * baseline_opportunity)
    utilization_imbalance = (utilization_a - utilization_b) / (2 * baseline_utilization)
    wait_shift = (
        number("wait_supply_weight") * imbalance[0]
        + number("wait_merchant_weight") * imbalance[1]
    )
    reliability_imbalance = (
        acceptance_delta + number("wait_reliability_weight") * wait_shift
    )
    result: Vector = (
        number("courier_persistence") * imbalance[0]
        + number("courier_response") * opportunity_imbalance,
        number("merchant_persistence") * imbalance[1]
        + number("merchant_response") * utilization_imbalance,
        number("demand_persistence") * imbalance[2]
        + number("customer_response") * reliability_imbalance,
    )
    lower = 1.0 - number("population_ceiling_ratio")
    upper = 1.0 - number("population_floor_ratio")
    return cast(Vector, tuple(max(lower, min(upper, value)) for value in result))


def _mechanism_jacobian(model: DeliveryMechanism, step: float = 1e-6) -> Matrix:
    columns: list[Vector] = []
    for index in range(3):
        positive = cast(
            Vector, tuple(step if item == index else 0.0 for item in range(3))
        )
        negative = cast(
            Vector, tuple(-step if item == index else 0.0 for item in range(3))
        )
        high = _mechanism_reference(model, positive)
        low = _mechanism_reference(model, negative)
        columns.append(
            cast(
                Vector,
                tuple((a - b) / (2.0 * step) for a, b in zip(high, low, strict=True)),
            )
        )
    return cast(
        Matrix,
        tuple(tuple(columns[column][row] for column in range(3)) for row in range(3)),
    )


def _matrix_payload(value: Matrix) -> list[list[float]]:
    return [list(row) for row in value]


def _eigen_payload(value: Matrix) -> tuple[list[dict[str, float]], float]:
    eigenvalues = matrix_eigenvalues(value)
    return (
        [{"real": item.real, "imaginary": item.imag} for item in eigenvalues],
        max(abs(item) for item in eigenvalues),
    )


def _noise_audit(
    innovations: dict[str, tuple[Vector, ...]],
    prior_states: dict[str, tuple[Vector, ...]],
    clamp_counts: dict[str, int],
) -> dict[str, object]:
    settings: dict[str, object] = {}
    all_pass = True
    for initial_id, vectors in innovations.items():
        components = tuple(
            tuple(value[index] for value in vectors) for index in range(3)
        )
        priors = prior_states[initial_id]
        n = len(vectors)
        correlation_limit = 4.0 / sqrt(n)
        component_rows: list[dict[str, object]] = []
        for index, values in enumerate(components):
            stats = distribution(values)
            standard_error = _numeric(stats["standard_deviation"]) / sqrt(n)
            mean_pass = abs(_numeric(stats["mean"])) <= 4.0 * standard_error
            variance_relative_error = abs(_numeric(stats["variance"]) - NOISE_SD**2) / (
                NOISE_SD**2
            )
            lag = autocorrelation(values, 1)
            component_pass = (
                mean_pass
                and variance_relative_error <= 0.20
                and abs(lag) <= correlation_limit
            )
            all_pass = all_pass and component_pass
            component_rows.append(
                {
                    "component": index,
                    "distribution": stats,
                    "standard_error": standard_error,
                    "mean_pass": mean_pass,
                    "variance_relative_error": variance_relative_error,
                    "autocorrelation": {
                        str(item): autocorrelation(values, item) for item in (1, 5, 10)
                    },
                    "state_dependence_correlation": correlation(
                        values, tuple(state[index] for state in priors)
                    ),
                    "pass": component_pass,
                }
            )
        cross = {
            f"{left}-{right}": correlation(components[left], components[right])
            for left, right in ((0, 1), (0, 2), (1, 2))
        }
        cross_pass = all(abs(value) <= correlation_limit for value in cross.values())
        clamp_pass = clamp_counts[initial_id] == 0
        all_pass = all_pass and cross_pass and clamp_pass
        settings[initial_id] = {
            "sample_count": n,
            "correlation_limit": correlation_limit,
            "components": component_rows,
            "cross_component_correlation": cross,
            "cross_component_pass": cross_pass,
            "clamp_count": clamp_counts[initial_id],
            "clamp_pass": clamp_pass,
            "innovation_covariance": _matrix_payload(covariance_matrix(vectors)),
        }
    return {"pass": all_pass, "settings": settings, "replay_equal": True}


def _deterministic_checks(
    layer: str, model: ReducedModel | DeliveryMechanism
) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for initial_id, initial in INITIALS:
        if layer == "R":
            states = (
                cast(ReducedModel, model)
                .simulate(
                    initial,
                    0.0,
                    1200,
                    41000,
                    0.0,
                    magnitude=max(abs(item) for item in initial),
                    direction_id=initial_id,
                )
                .states
            )
        else:
            states = (
                cast(DeliveryMechanism, model)
                .simulate(initial, 0.0, 1200, 41000, 0.0)
                .observations
            )
        initial_norm = sqrt(dot(initial, initial))
        final_norm = sqrt(dot(states[-1], states[-1]))
        passed = (
            final_norm <= 1e-14
            if initial_id == "zero"
            else final_norm <= 1e-8 * initial_norm
        )
        rows.append(
            {
                "initial_id": initial_id,
                "initial_norm": initial_norm,
                "final_norm": final_norm,
                "contraction_ratio": final_norm / max(initial_norm, 1e-30),
                "pass": passed,
            }
        )
    probe: Vector = (0.001, -0.0005, 0.00075)
    if layer == "R":
        expected = matvec(cast(ReducedModel, model).a, probe)
        observed = (
            cast(ReducedModel, model)
            .simulate(
                probe,
                0.0,
                1,
                41000,
                0.0,
                magnitude=0.001,
                direction_id="hand_reference",
            )
            .states[-1]
        )
    else:
        expected = _mechanism_reference(cast(DeliveryMechanism, model), probe)
        observed = (
            cast(DeliveryMechanism, model)
            .simulate(probe, 0.0, 1, 41000, 0.0)
            .observations[-1]
        )
    reference_error = max(abs(a - b) for a, b in zip(observed, expected, strict=True))
    return {
        "runs": rows,
        "one_step_reference": {
            "expected": expected,
            "observed": observed,
            "maximum_absolute_error": reference_error,
            "pass": reference_error <= 1e-12,
        },
        "pass": all(bool(row["pass"]) for row in rows) and reference_error <= 1e-12,
    }


def _trajectory_diagnostics(
    layer: str, model: ReducedModel | DeliveryMechanism
) -> dict[str, object]:
    trajectory_rows: list[dict[str, object]] = []
    horizon_rows: list[dict[str, object]] = []
    window_rows: list[dict[str, object]] = []
    placement_rows: list[dict[str, object]] = []
    innovation_lists: dict[str, list[Vector]] = {item[0]: [] for item in INITIALS}
    prior_lists: dict[str, list[Vector]] = {item[0]: [] for item in INITIALS}
    clamp_counts = {item[0]: 0 for item in INITIALS}
    stationary_zero_states: list[Vector] = []
    zero_magnitude_acf: list[dict[str, float]] = []
    zero_projection_acf: list[dict[str, float]] = []

    for seed in DIAGNOSTIC_SEEDS:
        for initial_id, initial in INITIALS:
            mechanism_states: tuple[MechanismState, ...] | None = None
            if layer == "R":
                states = (
                    cast(ReducedModel, model)
                    .simulate(
                        initial,
                        0.0,
                        HORIZONS[-1],
                        seed,
                        NOISE_SD,
                        magnitude=max(abs(item) for item in initial),
                        direction_id=initial_id,
                    )
                    .states
                )
                projection = _projection_r(cast(ReducedModel, model), states)
            else:
                run = cast(DeliveryMechanism, model).simulate(
                    initial, 0.0, HORIZONS[-1], seed, NOISE_SD
                )
                states = run.observations
                mechanism_states = run.states
                projection = _projection_m(cast(DeliveryMechanism, model), states)
            magnitudes = _magnitudes(states)
            trajectory_rows.append(
                {
                    "layer": layer,
                    "seed": seed,
                    "initial_id": initial_id,
                    "horizon": HORIZONS[-1],
                    "trace_digest": hashlib.sha256(
                        canonical_json(states).encode("utf-8")
                    ).hexdigest(),
                    "final_state": states[-1],
                }
            )
            for horizon in HORIZONS:
                selected_states = states[: horizon + 1]
                selected_projection = projection[: horizon + 1]
                row = _window_record(
                    layer,
                    seed,
                    initial_id,
                    selected_states[-300:],
                    selected_projection[-300:],
                )
                row["horizon"] = horizon
                horizon_rows.append(row)
            if initial_id == "zero":
                for window in WINDOWS:
                    row = _window_record(
                        layer,
                        seed,
                        initial_id,
                        states[1201 - window : 1201],
                        projection[1201 - window : 1201],
                    )
                    row["window"] = window
                    window_rows.append(row)
                for start in PLACEMENTS:
                    row = _window_record(
                        layer,
                        seed,
                        initial_id,
                        states[start : start + 300],
                        projection[start : start + 300],
                    )
                    row["burn_in"] = start
                    placement_rows.append(row)
                stationary_zero_states.extend(states[-4800:])
                final_magnitudes = magnitudes[-4800:]
                final_projection = projection[-4800:]
                zero_magnitude_acf.append(
                    {
                        str(lag): autocorrelation(final_magnitudes, lag)
                        for lag in (1, 5, 10, 30)
                    }
                )
                zero_projection_acf.append(
                    {
                        str(lag): autocorrelation(final_projection, lag)
                        for lag in (1, 5, 10, 30)
                    }
                )
            for index in range(len(states) - 4800, len(states)):
                before = states[index - 1]
                if layer == "R":
                    deterministic = matvec(cast(ReducedModel, model).a, before)
                else:
                    deterministic = _mechanism_reference(
                        cast(DeliveryMechanism, model), before
                    )
                innovation = cast(
                    Vector,
                    tuple(
                        actual - expected
                        for actual, expected in zip(
                            states[index], deterministic, strict=True
                        )
                    ),
                )
                innovation_lists[initial_id].append(innovation)
                prior_lists[initial_id].append(before)
                if (
                    layer == "M"
                    and mechanism_states is not None
                    and any(abs(value) >= 0.8 - 1e-15 for value in states[index])
                ):
                    clamp_counts[initial_id] += 1

    noise = _noise_audit(
        {key: tuple(value) for key, value in innovation_lists.items()},
        {key: tuple(value) for key, value in prior_lists.items()},
        clamp_counts,
    )
    return {
        "trajectories": trajectory_rows,
        "horizon_records": horizon_rows,
        "window_records": window_rows,
        "placement_records": placement_rows,
        "stationary_zero_states": stationary_zero_states,
        "state_autocorrelation": {
            "magnitude": {
                lag: fmean(row[lag] for row in zero_magnitude_acf)
                for lag in ("1", "5", "10", "30")
            },
            "projection": {
                lag: fmean(row[lag] for row in zero_projection_acf)
                for lag in ("1", "5", "10", "30")
            },
        },
        "noise_audit": noise,
    }


def _aggregate_records(
    records: list[dict[str, object]], key: str, values: tuple[int, ...]
) -> dict[str, object]:
    result: dict[str, object] = {}
    for value in values:
        selected = [
            item
            for item in records
            if item.get(key) == value and item.get("initial_id") == "zero"
        ]
        result[str(value)] = {
            "count": len(selected),
            "mean_imbalance": fmean(
                _numeric(item["imbalance_mean"]) for item in selected
            ),
            "mean_variance": fmean(
                _numeric(item["imbalance_variance"]) for item in selected
            ),
            "magnitude_pass_rate": fmean(
                bool(cast(dict[str, object], item["components"])["magnitude_pass"])
                for item in selected
            ),
            "slope_pass_rate": fmean(
                bool(cast(dict[str, object], item["components"])["slope_pass"])
                for item in selected
            ),
            "window_pass_rate": fmean(
                bool(cast(dict[str, object], item["components"])["window_pass"])
                for item in selected
            ),
            "all_pass_rate": fmean(
                bool(cast(dict[str, object], item["components"])["all_pass"])
                for item in selected
            ),
        }
    return result


def _horizon_slope_interval(
    records: list[dict[str, object]], metric: str, seed: int
) -> tuple[float, float]:
    by_seed = {
        diagnostic_seed: {
            _integer(item["horizon"]): _numeric(item[metric])
            for item in records
            if item.get("seed") == diagnostic_seed and item.get("initial_id") == "zero"
        }
        for diagnostic_seed in DIAGNOSTIC_SEEDS
    }
    rng = random.Random(seed)
    estimates: list[float] = []
    for _ in range(1000):
        sampled = tuple(rng.choice(DIAGNOSTIC_SEEDS) for _ in DIAGNOSTIC_SEEDS)
        ensemble = tuple(
            fmean(by_seed[item][horizon] for item in sampled) for horizon in HORIZONS
        )
        estimates.append(ols_slope(ensemble))
    ordered = sorted(estimates)
    return quantile(tuple(ordered), 0.025), quantile(tuple(ordered), 0.975)


def _summarize_sensitivities(
    raw: dict[str, object], layer_offset: int
) -> dict[str, object]:
    horizon_records = cast(list[dict[str, object]], raw["horizon_records"])
    window_records = cast(list[dict[str, object]], raw["window_records"])
    placement_records = cast(list[dict[str, object]], raw["placement_records"])
    horizon = _aggregate_records(horizon_records, "horizon", HORIZONS)
    window = _aggregate_records(window_records, "window", WINDOWS)
    placement = _aggregate_records(placement_records, "burn_in", PLACEMENTS)
    first = cast(dict[str, object], horizon[str(HORIZONS[0])])
    last = cast(dict[str, object], horizon[str(HORIZONS[-1])])
    return {
        "horizon": {
            "aggregates": horizon,
            "mean_ratio_8x_1x": _numeric(last["mean_imbalance"])
            / max(_numeric(first["mean_imbalance"]), 1e-30),
            "variance_ratio_8x_1x": _numeric(last["mean_variance"])
            / max(_numeric(first["mean_variance"]), 1e-30),
            "mean_bootstrap_slope_ci95": _horizon_slope_interval(
                horizon_records, "imbalance_mean", 44000 + layer_offset
            ),
            "variance_bootstrap_slope_ci95": _horizon_slope_interval(
                horizon_records, "imbalance_variance", 45000 + layer_offset
            ),
        },
        "window": {"aggregates": window},
        "placement": {"aggregates": placement},
    }


def _replay_and_slope_analysis(
    layer: str,
    model: ReducedModel | DeliveryMechanism,
    archived: tuple[RunSummary, ...],
) -> dict[str, object]:
    archived_by_seed = {item.seed: item for item in archived}
    slope_rows: list[dict[str, object]] = []
    digest_matches: dict[str, bool] = {}
    for index, seed in enumerate(range(21000, 21064)):
        initial: Vector = (0.0, 0.0, 0.0)
        if layer == "R":
            states = (
                cast(ReducedModel, model)
                .simulate(
                    initial,
                    0.0,
                    1200,
                    seed,
                    NOISE_SD,
                    magnitude=0.0,
                    direction_id="zero",
                )
                .states
            )
            projection = _projection_r(cast(ReducedModel, model), states)
        else:
            states = (
                cast(DeliveryMechanism, model)
                .simulate(initial, 0.0, 1200, seed, NOISE_SD)
                .observations
            )
            projection = _projection_m(cast(DeliveryMechanism, model), states)
        trace_digest = hashlib.sha256(
            canonical_json(states).encode("utf-8")
        ).hexdigest()
        digest_matches[str(seed)] = trace_digest == archived_by_seed[seed].trace_digest
        magnitudes = _magnitudes(states[-300:])
        gate_summary = _summary_from_states(
            layer, 0.0, seed, "zero", states, projection, {}, 300
        )
        if abs(gate_summary.slope - archived_by_seed[seed].slope) > 1e-18:
            raise ResearchGateError("REPLAY_FAILURE", f"{layer} seed {seed} slope")
        interval = moving_block_slope_interval(
            magnitudes,
            block_length=30,
            samples=1000,
            seed=43000 + (10000 if layer == "M" else 0) + index,
        )
        slope_rows.append(
            {
                "seed": seed,
                "ols": ols_slope(magnitudes),
                "theil_sen": theil_sen_slope(magnitudes),
                "mean_first_difference": mean_first_difference(magnitudes),
                "block_averaged": block_averaged_slope(magnitudes),
                "moving_block_ci95": interval,
                "distinguishable_from_zero": interval[0] > 0.0 or interval[1] < 0.0,
            }
        )
    required_replay = all(digest_matches[str(seed)] for seed in REPLAY_SEEDS)
    estimator_distributions = {
        estimator: distribution(tuple(_numeric(row[estimator]) for row in slope_rows))
        for estimator in ("ols", "theil_sen", "mean_first_difference", "block_averaged")
    }
    return {
        "required_seeds": REPLAY_SEEDS,
        "required_replay_pass": required_replay,
        "all_64_replay_pass": all(digest_matches.values()),
        "digest_matches": digest_matches,
        "fraction_slope_distinguishable_from_zero": fmean(
            bool(row["distinguishable_from_zero"]) for row in slope_rows
        ),
        "estimators": estimator_distributions,
        "records": slope_rows,
    }


def _candidate_restored(summary: RunSummary, magnitudes: tuple[float, ...]) -> bool:
    difference = summary.final_third_mean - summary.preceding_third_mean
    if abs(difference) <= 0.10 * EPSILON:
        drift_pass = True
    else:
        interval = moving_block_difference_interval(
            magnitudes,
            block_length=30,
            samples=1000,
            seed=49999 + summary.seed,
        )
        drift_pass = interval[0] <= 0.0 <= interval[1]
    return (
        all(
            isfinite(value)
            for value in (
                summary.imbalance_mean,
                summary.imbalance_variance,
                summary.final_third_mean,
                summary.preceding_third_mean,
            )
        )
        and summary.imbalance_mean <= EPSILON
        and summary.imbalance_variance <= EPSILON**2 / 4.0
        and drift_pass
    )


def _synthetic_controls() -> dict[str, object]:
    stable_labels: list[str] = []
    locked_labels: list[str] = []
    stable_candidate = 0
    locked_candidate = 0
    stable_trace_digests: list[str] = []
    for seed in SYNTHETIC_SEEDS:
        rng = random.Random(seed)
        stable_states: list[Vector] = [(0.0, 0.0, 0.0)]
        for _ in range(1200):
            stable_states.append(
                cast(
                    Vector,
                    tuple(
                        0.65 * value + rng.gauss(0.0, NOISE_SD)
                        for value in stable_states[-1]
                    ),
                )
            )
        stable_tuple = tuple(stable_states)
        stable_projection = tuple(sum(value) for value in stable_tuple)
        stable_summary = _summary_from_states(
            "S", 0.0, seed, "stable", stable_tuple, stable_projection, {}, 300
        )
        stable_labels.append(_classify(stable_summary, EPSILON))
        stable_candidate += _candidate_restored(
            stable_summary, _magnitudes(stable_tuple[-300:])
        )
        stable_trace_digests.append(
            hashlib.sha256(canonical_json(stable_tuple).encode("utf-8")).hexdigest()
        )

        sign = 1.0 if seed % 2 == 0 else -1.0
        rng = random.Random(seed)
        locked_states: list[Vector] = [(0.05 * sign,) * 3]
        for _ in range(1200):
            locked_states.append(
                cast(
                    Vector,
                    tuple(
                        0.95 * value + 0.0025 * sign + rng.gauss(0.0, NOISE_SD)
                        for value in locked_states[-1]
                    ),
                )
            )
        locked_tuple = tuple(locked_states)
        locked_projection = tuple(sum(value) for value in locked_tuple)
        locked_summary = _summary_from_states(
            "S", 0.0, seed, "locked", locked_tuple, locked_projection, {}, 300
        )
        locked_labels.append(_classify(locked_summary, EPSILON))
        locked_candidate += _candidate_restored(
            locked_summary, _magnitudes(locked_tuple[-300:])
        )

    stable_success = sum(label == "RESTORED" for label in stable_labels)
    locked_success = sum(label == "LOCKED" for label in locked_labels)
    candidate_stable = stable_candidate / len(SYNTHETIC_SEEDS)
    candidate_specificity = 1.0 - locked_candidate / len(SYNTHETIC_SEEDS)
    stable_wilson = _wilson(stable_candidate, len(SYNTHETIC_SEEDS))
    specificity_wilson = _wilson(
        len(SYNTHETIC_SEEDS) - locked_candidate, len(SYNTHETIC_SEEDS)
    )
    replay_rng = random.Random(SYNTHETIC_SEEDS[0])
    replay_states: list[Vector] = [(0.0, 0.0, 0.0)]
    for _ in range(1200):
        replay_states.append(
            cast(
                Vector,
                tuple(
                    0.65 * value + replay_rng.gauss(0.0, NOISE_SD)
                    for value in replay_states[-1]
                ),
            )
        )
    replay_digest = hashlib.sha256(
        canonical_json(tuple(replay_states)).encode("utf-8")
    ).hexdigest()
    return {
        "stable": {
            "spectral_radius": 0.65,
            "label_distribution": dict(Counter(stable_labels)),
            "restored_sensitivity": stable_success / len(SYNTHETIC_SEEDS),
            "false_negative_rate": 1.0 - stable_success / len(SYNTHETIC_SEEDS),
        },
        "locked": {
            "label_distribution": dict(Counter(locked_labels)),
            "locked_sensitivity": locked_success / len(SYNTHETIC_SEEDS),
            "specificity": locked_success / len(SYNTHETIC_SEEDS),
            "false_positive_rate": sum(label == "RESTORED" for label in locked_labels)
            / len(SYNTHETIC_SEEDS),
        },
        "candidate_criterion": {
            "stable_sensitivity": candidate_stable,
            "stable_wilson95": stable_wilson,
            "locked_specificity": candidate_specificity,
            "specificity_wilson95": specificity_wilson,
            "reference_valid": candidate_stable >= 0.90
            and stable_wilson[0] > 0.80
            and candidate_specificity >= 0.90
            and specificity_wilson[0] > 0.80,
        },
        "deterministic_replay": replay_digest == stable_trace_digests[0],
    }


def _classifier_self_check() -> dict[str, object]:
    def fixture(
        *,
        imbalance_mean: float,
        slope: float,
        preceding_third_mean: float,
        final_third_mean: float,
    ) -> RunSummary:
        return RunSummary(
            "S",
            0.0,
            0,
            "fixture",
            (0.0, 0.0, 0.0),
            imbalance_mean,
            0.01,
            1e-8,
            1.0,
            0.01,
            0.01,
            slope,
            preceding_third_mean,
            final_third_mean,
            "fixture",
            {},
        )

    cases = (
        (
            "restored",
            fixture(
                imbalance_mean=0.01,
                slope=-1e-6,
                preceding_third_mean=0.01,
                final_third_mean=0.009,
            ),
            "RESTORED",
        ),
        (
            "slope_reject",
            fixture(
                imbalance_mean=0.01,
                slope=1e-6,
                preceding_third_mean=0.01,
                final_third_mean=0.009,
            ),
            "AMBIGUOUS",
        ),
        (
            "window_reject",
            fixture(
                imbalance_mean=0.01,
                slope=-1e-6,
                preceding_third_mean=0.009,
                final_third_mean=0.01,
            ),
            "AMBIGUOUS",
        ),
        (
            "locked",
            fixture(
                imbalance_mean=0.05,
                slope=0.0,
                preceding_third_mean=0.05,
                final_third_mean=0.05,
            ),
            "LOCKED",
        ),
    )
    rows = [
        {
            "case": name,
            "expected": expected,
            "observed": _classify(summary, EPSILON),
            "pass": _classify(summary, EPSILON) == expected,
        }
        for name, summary, expected in cases
    ]
    return {"pass": all(bool(row["pass"]) for row in rows), "cases": rows}


def _analytical_result(
    layer: str,
    model: ReducedModel | DeliveryMechanism,
    stationary_states: tuple[Vector, ...],
    noise_audit: dict[str, object],
) -> dict[str, object]:
    if layer == "R":
        transition = cast(ReducedModel, model).a
        innovation = diagonal_matrix(NOISE_SD**2)
    else:
        transition = _mechanism_jacobian(cast(DeliveryMechanism, model))
        settings = cast(dict[str, object], noise_audit["settings"])
        zero = cast(dict[str, object], settings["zero"])
        innovation = cast(
            Matrix,
            tuple(
                tuple(float(item) for item in row)
                for row in cast(list[list[float]], zero["innovation_covariance"])
            ),
        )
    eigenvalues, radius = _eigen_payload(transition)
    predicted, iterations = solve_discrete_lyapunov(transition, innovation)
    observed = covariance_matrix(stationary_states)
    return {
        "transition_matrix": _matrix_payload(transition),
        "eigenvalues": eigenvalues,
        "spectral_radius": radius,
        "deterministically_stable": radius < 1.0,
        "innovation_covariance": _matrix_payload(innovation),
        "predicted_stationary_covariance": _matrix_payload(predicted),
        "observed_stationary_covariance": _matrix_payload(observed),
        "covariance_relative_error": relative_matrix_error(observed, predicted),
        "lyapunov_iterations": iterations,
    }


def _rate_range(aggregates: dict[str, object], field: str) -> float:
    values = [
        _numeric(cast(dict[str, object], item)[field]) for item in aggregates.values()
    ]
    return max(values) - min(values)


def _mean_ratio(aggregates: dict[str, object]) -> float:
    values = [
        _numeric(cast(dict[str, object], item)["mean_imbalance"])
        for item in aggregates.values()
    ]
    return max(values) / max(min(values), 1e-30)


def _root_cause(
    layer: str,
    decomposition: dict[str, object],
    replay: dict[str, object],
    deterministic: dict[str, object],
    analytical: dict[str, object],
    sensitivities: dict[str, object],
    noise: dict[str, object],
    synthetic: dict[str, object],
    classifier_check: dict[str, object],
) -> dict[str, object]:
    horizon = cast(dict[str, object], sensitivities["horizon"])
    horizon_aggregates = cast(dict[str, object], horizon["aggregates"])
    window = cast(dict[str, object], sensitivities["window"])
    placement = cast(dict[str, object], sensitivities["placement"])
    window_aggregates = cast(dict[str, object], window["aggregates"])
    placement_aggregates = cast(dict[str, object], placement["aggregates"])
    first_h = cast(dict[str, object], horizon_aggregates["1200"])
    last_h = cast(dict[str, object], horizon_aggregates["9600"])
    first_b = cast(dict[str, object], placement_aggregates["0"])
    last_b = cast(dict[str, object], placement_aggregates["900"])
    counts = cast(dict[str, object], decomposition["counts"])
    stable = cast(dict[str, object], synthetic["stable"])
    locked = cast(dict[str, object], synthetic["locked"])
    mean_ci = cast(tuple[float, float], horizon["mean_bootstrap_slope_ci95"])
    variance_ci = cast(tuple[float, float], horizon["variance_bootstrap_slope_ci95"])
    replay_failure = not bool(replay["required_replay_pass"])
    model_bug = not bool(deterministic["pass"])
    classifier_bug = not bool(classifier_check["pass"])
    numerical = model_bug
    unstable = _numeric(analytical["spectral_radius"]) >= 1.0 or (
        mean_ci[0] > 0.0
        and variance_ci[0] > 0.0
        and _numeric(horizon["mean_ratio_8x_1x"]) > 1.5
        and _numeric(horizon["variance_ratio_8x_1x"]) > 1.5
    )
    state_mean = _numeric(last_h["mean_imbalance"])
    noise_mismatch = not bool(noise["pass"]) and state_mean > 0.10 * EPSILON
    insufficient = (
        _numeric(last_h["all_pass_rate"]) - _numeric(first_h["all_pass_rate"]) >= 0.30
        and _numeric(last_h["all_pass_rate"]) >= 0.80
        and _numeric(last_h["mean_imbalance"])
        <= 0.50 * _numeric(first_h["mean_imbalance"])
    )
    burn_in = (
        _numeric(first_b["all_pass_rate"]) < 0.50
        and _numeric(last_b["all_pass_rate"]) >= 0.80
        and _numeric(last_b["all_pass_rate"]) - _numeric(first_b["all_pass_rate"])
        >= 0.30
    )
    mismatch = (
        _numeric(analytical["spectral_radius"]) < 1.0
        and bool(deterministic["pass"])
        and _numeric(horizon["mean_ratio_8x_1x"]) < 1.5
        and _numeric(horizon["variance_ratio_8x_1x"]) < 1.5
        and bool(noise["pass"])
        and _integer(counts["magnitude_pass"]) / 64.0 >= 0.95
        and _integer(counts["all_pass"]) / 64.0 <= 0.50
        and _numeric(stable["false_negative_rate"]) >= 0.50
        and _numeric(locked["locked_sensitivity"]) >= 0.80
    )
    finite_window = (
        max(
            _rate_range(window_aggregates, "all_pass_rate"),
            _rate_range(placement_aggregates, "all_pass_rate"),
        )
        >= 0.25
        and max(_mean_ratio(window_aggregates), _mean_ratio(placement_aggregates))
        <= 1.25
    )
    if replay_failure:
        primary = "REPLAY_FAILURE"
    elif model_bug:
        primary = "MODEL_IMPLEMENTATION_BUG"
    elif classifier_bug:
        primary = "CLASSIFIER_IMPLEMENTATION_BUG"
    elif numerical:
        primary = "NUMERICAL_ARTIFACT"
    elif unstable:
        primary = "DYNAMICAL_INSTABILITY"
    elif noise_mismatch:
        primary = "NOISE_MODEL_MISMATCH"
    elif insufficient:
        primary = "INSUFFICIENT_HORIZON"
    elif burn_in:
        primary = "BURN_IN_ARTIFACT"
    elif mismatch:
        primary = "STABLE_STOCHASTIC_EQUILIBRIUM_CLASSIFIER_MISMATCH"
    elif finite_window:
        primary = "FINITE_WINDOW_ARTIFACT"
    else:
        primary = "INCONCLUSIVE"
    secondary = tuple(
        name
        for name, supported in (
            ("FINITE_WINDOW_ARTIFACT", finite_window),
            ("BURN_IN_ARTIFACT", burn_in),
            ("INSUFFICIENT_HORIZON", insufficient),
            ("NOISE_MODEL_MISMATCH", noise_mismatch),
        )
        if supported and name != primary
    )
    return {
        "layer": layer,
        "primary": primary,
        "secondary": secondary,
        "decision_flags": {
            "replay_failure": replay_failure,
            "model_bug": model_bug,
            "classifier_bug": classifier_bug,
            "numerical_artifact": numerical,
            "dynamical_instability": unstable,
            "noise_model_mismatch": noise_mismatch,
            "insufficient_horizon": insufficient,
            "burn_in_artifact": burn_in,
            "stable_stochastic_classifier_mismatch": mismatch,
            "finite_window_artifact": finite_window,
        },
    }


def _artifact_reference(item: StoredArtifact) -> dict[str, str]:
    return {
        "relative_path": item.relative_path,
        "sha256": item.sha256,
        "content_digest": item.content_digest,
    }


def _residual_variance_shares(noise: dict[str, object]) -> dict[str, float]:
    settings = cast(dict[str, object], noise["settings"])
    zero = cast(dict[str, object], settings["zero"])
    components = cast(list[dict[str, object]], zero["components"])
    variances = tuple(
        _numeric(cast(dict[str, object], item["distribution"])["variance"])
        for item in components
    )
    total = sum(variances)
    names = ("courier", "merchant", "demand")
    return {
        name: value / max(total, 1e-30)
        for name, value in zip(names, variances, strict=True)
    }


def run_negative_control_diagnostic(
    package_root: Path,
    preregistration: Preregistration,
    store: ArtifactStore,
) -> dict[str, object]:
    repository_root = package_root.parents[2]
    diagnostic_root = store.class_root("diagnostic") / "negative_control"
    if diagnostic_root.exists() and any(diagnostic_root.iterdir()):
        raise ResearchGateError("DIAGNOSTIC_ARTIFACT_EXISTS", str(diagnostic_root))
    repository_inputs = _verify_repository_inputs(package_root)
    frozen_inputs = verify_frozen_inputs(package_root, store)
    gate2_summary, gate2_artifact = store.read_json(
        "confirmatory",
        "gate2_long_horizon/gate2_validation.json",
        expected_sha256=GATE2_EXTERNAL_SUMMARY_SHA256,
    )
    if (
        gate2_summary.get("status") != "FAIL"
        or gate2_summary.get("gate3_eligibility") != "NO"
    ):
        raise ResearchGateError("DIAGNOSTIC_INPUT_MISMATCH", "Gate 2 status changed")

    payload = preregistration.payload
    layer_r = ReducedModel.from_config(cast(dict[str, object], payload["layer_r"]))
    layer_m = DeliveryMechanism.from_config(cast(dict[str, object], payload["layer_m"]))
    archived_r, archived_r_artifact = _load_archived_controls(store, "R")
    archived_m, archived_m_artifact = _load_archived_controls(store, "M")
    decomposition_r = _decomposition(archived_r)
    decomposition_m = _decomposition(archived_m)
    classifier_check = _classifier_self_check()
    replay_r = _replay_and_slope_analysis("R", layer_r, archived_r)
    replay_m = _replay_and_slope_analysis("M", layer_m, archived_m)
    deterministic_r = _deterministic_checks("R", layer_r)
    deterministic_m = _deterministic_checks("M", layer_m)
    raw_r = _trajectory_diagnostics("R", layer_r)
    raw_m = _trajectory_diagnostics("M", layer_m)
    sensitivities_r = _summarize_sensitivities(raw_r, 0)
    sensitivities_m = _summarize_sensitivities(raw_m, 10000)
    noise_r = cast(dict[str, object], raw_r["noise_audit"])
    noise_m = cast(dict[str, object], raw_m["noise_audit"])
    stationary_r = tuple(cast(list[Vector], raw_r["stationary_zero_states"]))
    stationary_m = tuple(cast(list[Vector], raw_m["stationary_zero_states"]))
    analytical_r = _analytical_result("R", layer_r, stationary_r, noise_r)
    analytical_m = _analytical_result("M", layer_m, stationary_m, noise_m)
    synthetic = _synthetic_controls()
    root_r = _root_cause(
        "R",
        decomposition_r,
        replay_r,
        deterministic_r,
        analytical_r,
        sensitivities_r,
        noise_r,
        synthetic,
        classifier_check,
    )
    root_m = _root_cause(
        "M",
        decomposition_m,
        replay_m,
        deterministic_m,
        analytical_m,
        sensitivities_m,
        noise_m,
        synthetic,
        classifier_check,
    )
    primary_r = str(root_r["primary"])
    primary_m = str(root_m["primary"])
    if primary_r == primary_m:
        primary = primary_r
    elif "INCONCLUSIVE" in (primary_r, primary_m):
        primary = "INCONCLUSIVE"
    else:
        primary = "MULTIPLE_CAUSES"
    if primary in {"DYNAMICAL_INSTABILITY", "MODEL_IMPLEMENTATION_BUG"}:
        verdict = "FAIL"
    elif primary == "INCONCLUSIVE":
        verdict = "INCONCLUSIVE"
    else:
        verdict = "PASS"
    candidate = cast(dict[str, object], synthetic["candidate_criterion"])
    replay_pass = bool(replay_r["required_replay_pass"]) and bool(
        replay_m["required_replay_pass"]
    )
    gate2b = (
        "CONDITIONAL"
        if verdict == "PASS"
        and bool(candidate["reference_valid"])
        and replay_pass
        and bool(deterministic_r["pass"])
        and bool(deterministic_m["pass"])
        else "NO"
    )

    decomposition_payload: dict[str, object] = {
        "protocol_id": PROTOCOL_ID,
        "layer_r": decomposition_r,
        "layer_m": decomposition_m,
        "classifier_self_check": classifier_check,
        "source_artifacts": {
            "R": _artifact_reference(archived_r_artifact),
            "M": _artifact_reference(archived_m_artifact),
        },
    }
    horizon_payload: dict[str, object] = {
        "protocol_id": PROTOCOL_ID,
        "layer_r": sensitivities_r["horizon"],
        "layer_m": sensitivities_m["horizon"],
    }
    window_payload: dict[str, object] = {
        "protocol_id": PROTOCOL_ID,
        "layer_r": {
            "window": sensitivities_r["window"],
            "placement": sensitivities_r["placement"],
        },
        "layer_m": {
            "window": sensitivities_m["window"],
            "placement": sensitivities_m["placement"],
        },
    }
    stationary_payload: dict[str, object] = {
        "protocol_id": PROTOCOL_ID,
        "layer_r": {
            "analytical": analytical_r,
            "noise_audit": noise_r,
            "state_autocorrelation": raw_r["state_autocorrelation"],
        },
        "layer_m": {
            "analytical": analytical_m,
            "noise_audit": noise_m,
            "state_autocorrelation": raw_m["state_autocorrelation"],
            "residual_variance_shares": _residual_variance_shares(noise_m),
            "not_modeled": ["separate_stochastic_arrivals", "service_time_noise"],
        },
    }
    layer_r_payload: dict[str, object] = {
        "protocol_id": PROTOCOL_ID,
        "deterministic": deterministic_r,
        "replay_and_slope": replay_r,
        "trajectories": raw_r["trajectories"],
        "horizon_records": raw_r["horizon_records"],
        "window_records": raw_r["window_records"],
        "placement_records": raw_r["placement_records"],
        "root_cause": root_r,
    }
    layer_m_payload: dict[str, object] = {
        "protocol_id": PROTOCOL_ID,
        "deterministic": deterministic_m,
        "replay_and_slope": replay_m,
        "trajectories": raw_m["trajectories"],
        "horizon_records": raw_m["horizon_records"],
        "window_records": raw_m["window_records"],
        "placement_records": raw_m["placement_records"],
        "root_cause": root_m,
    }
    artifacts = (
        store.write_json(
            "diagnostic",
            "negative_control/classifier_decomposition/gate2-controls.json",
            decomposition_payload,
        ),
        store.write_json(
            "diagnostic",
            "negative_control/horizon_sensitivity/results.json",
            horizon_payload,
        ),
        store.write_json(
            "diagnostic",
            "negative_control/window_sensitivity/results.json",
            window_payload,
        ),
        store.write_json(
            "diagnostic",
            "negative_control/stationary_analysis/results.json",
            stationary_payload,
        ),
        store.write_json(
            "diagnostic",
            "negative_control/synthetic_controls/results.json",
            synthetic,
        ),
        store.write_json(
            "diagnostic", "negative_control/layer_r/analysis.json", layer_r_payload
        ),
        store.write_json(
            "diagnostic", "negative_control/layer_m/analysis.json", layer_m_payload
        ),
    )
    counts_r = cast(dict[str, object], decomposition_r["counts"])
    counts_m = cast(dict[str, object], decomposition_m["counts"])
    summary: dict[str, object] = {
        "protocol_id": PROTOCOL_ID,
        "stage": "post-confirmatory-negative-control-diagnostic",
        "artifact_class": "diagnostic",
        "diagnostic_verdict": verdict,
        "original_gate2": "FAIL",
        "original_gate2_unchanged": True,
        "gate2b_eligibility": gate2b,
        "gate3_eligibility": "NO",
        "primary_root_cause": primary,
        "layers": {"R": root_r, "M": root_m},
        "analytical": {"R": analytical_r, "M": analytical_m},
        "decomposition_counts": {
            "R": decomposition_r["counts"],
            "M": decomposition_m["counts"],
        },
        "observed_long_run_imbalance": {
            "R": fmean(item.imbalance_mean for item in archived_r),
            "M": fmean(item.imbalance_mean for item in archived_m),
        },
        "original_false_negative_rates": {
            "R": {
                "slope_condition": 1.0 - _integer(counts_r["slope_pass"]) / 64.0,
                "window_condition": 1.0 - _integer(counts_r["window_pass"]) / 64.0,
                "all_conditions": 1.0 - _integer(counts_r["all_pass"]) / 64.0,
            },
            "M": {
                "slope_condition": 1.0 - _integer(counts_m["slope_pass"]) / 64.0,
                "window_condition": 1.0 - _integer(counts_m["window_pass"]) / 64.0,
                "all_conditions": 1.0 - _integer(counts_m["all_pass"]) / 64.0,
            },
        },
        "synthetic_controls": synthetic,
        "implementation_defect_found": not bool(deterministic_r["pass"])
        or not bool(deterministic_m["pass"])
        or not bool(classifier_check["pass"]),
        "replay": {
            "status": "PASS" if replay_pass else "FAIL",
            "R": replay_r["required_replay_pass"],
            "M": replay_m["required_replay_pass"],
        },
        "frozen_inputs": {
            "repository": repository_inputs,
            "gate1": frozen_inputs,
            "gate2_external": _artifact_reference(gate2_artifact),
        },
        "implementation_commit": _git(repository_root, "rev-parse", "HEAD"),
        "worktree_disclosure": _git(
            repository_root, "status", "--short", "--untracked-files=normal"
        ),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "generated_at": datetime.now(UTC).isoformat(),
        "bulk_artifacts": [_artifact_reference(item) for item in artifacts],
        "claim_limit": (
            "Diagnostic success does not alter Gate 2 FAIL, authorize Gate 3, "
            "or establish scientific novelty"
        ),
    }
    summary_artifact = store.write_json(
        "diagnostic", "negative_control/negative_control_diagnostic.json", summary
    )
    return {
        "status": verdict,
        "original_gate2": "FAIL",
        "primary_root_cause": primary,
        "layer_r_root_cause": primary_r,
        "layer_m_root_cause": primary_m,
        "gate2b_eligibility": gate2b,
        "gate3_eligibility": "NO",
        "relative_path": summary_artifact.relative_path,
        "sha256": summary_artifact.sha256,
        "content_digest": summary_artifact.content_digest,
    }
