from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from itertools import pairwise
from math import isclose, isfinite, sqrt
from pathlib import Path
from statistics import fmean, median, pstdev
from typing import cast

from .artifacts import ArtifactStore, StoredArtifact
from .linalg import Vector, dot
from .mechanism import DeliveryMechanism, MechanismRun, OperationalMetrics
from .preregistration import Preregistration, canonical_json
from .reason_codes import ResearchGateError
from .reduced_model import ReducedModel

FROZEN_REPORT_SHA256 = (
    "4a86d0c0989c8512182665e49f34f6aa35a83a2fcc5841e3534fada37f6d7656"
)
FROZEN_THRESHOLD_SHA256 = (
    "85c06e9186a069739b75be40015b2c53350bc589c16121151d2c71aca812a8bb"
)
FROZEN_R_ALPHA = 2.60097908919399
FROZEN_R_INTERVAL = (2.59684653524659, 2.60537444184453)
FROZEN_M_ALPHA = 3.29064597856242
FROZEN_M_INTERVAL = (3.28304848117258, 3.29797102241973)
COARSE_MULTIPLIERS = (0.40, 0.60, 0.80, 0.90, 0.95, 1.00, 1.05, 1.10, 1.20, 1.40, 1.60)
FINE_MULTIPLIERS = tuple(0.90 + 0.025 * index for index in range(9))
INITIALS: tuple[tuple[str, Vector], ...] = (
    ("zero", (0.0, 0.0, 0.0)),
    ("positive", (0.01, 0.01, 0.01)),
    ("negative", (-0.01, -0.01, -0.01)),
    ("positive_half", (0.005, 0.005, 0.005)),
    ("negative_half", (-0.005, -0.005, -0.005)),
)


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ResearchGateError("FROZEN_INPUT_MISMATCH", f"{name} is not numeric")
    return float(value)


def _int_list(value: object, name: str) -> tuple[int, ...]:
    if not isinstance(value, list) or any(
        isinstance(item, bool) or not isinstance(item, int) for item in value
    ):
        raise ResearchGateError(
            "FROZEN_INPUT_MISMATCH", f"{name} is not an integer list"
        )
    return tuple(value)


def _float_list(value: object, name: str) -> tuple[float, ...]:
    if not isinstance(value, list) or any(
        isinstance(item, bool) or not isinstance(item, (float, int)) for item in value
    ):
        raise ResearchGateError(
            "FROZEN_INPUT_MISMATCH", f"{name} is not a numeric list"
        )
    return tuple(float(item) for item in value)


@dataclass(frozen=True, slots=True)
class RunSummary:
    layer: str
    alpha: float
    seed: int
    initial_id: str
    final_state: Vector
    imbalance_mean: float
    imbalance_median: float
    imbalance_variance: float
    sign_persistence: float
    projection_mean: float
    projection_final: float
    slope: float
    preceding_third_mean: float
    final_third_mean: float
    trace_digest: str
    operational: dict[str, float]
    classification: str = "UNCLASSIFIED"

    def payload(self) -> dict[str, object]:
        return {
            "layer": self.layer,
            "alpha": self.alpha,
            "seed": self.seed,
            "initial_id": self.initial_id,
            "final_state": self.final_state,
            "imbalance_mean": self.imbalance_mean,
            "imbalance_median": self.imbalance_median,
            "imbalance_variance": self.imbalance_variance,
            "sign_persistence": self.sign_persistence,
            "projection_mean": self.projection_mean,
            "projection_final": self.projection_final,
            "slope": self.slope,
            "preceding_third_mean": self.preceding_third_mean,
            "final_third_mean": self.final_third_mean,
            "trace_digest": self.trace_digest,
            "operational": self.operational,
            "classification": self.classification,
        }


@dataclass(frozen=True, slots=True)
class AlphaAggregate:
    alpha: float
    multiplier: float
    epsilon_sym: float
    robust_label: str
    restored_count: int
    locked_count: int
    seed_count: int
    wilson_restored: tuple[float, float]
    wilson_locked: tuple[float, float]
    path_fraction: float
    path_wilson: tuple[float, float]
    path_dependence: bool
    zero_restored: bool
    operational: dict[str, float]
    records: tuple[RunSummary, ...]

    def payload(self) -> dict[str, object]:
        return {
            "alpha": self.alpha,
            "multiplier": self.multiplier,
            "epsilon_sym": self.epsilon_sym,
            "robust_label": self.robust_label,
            "restored_count": self.restored_count,
            "locked_count": self.locked_count,
            "seed_count": self.seed_count,
            "wilson_restored": self.wilson_restored,
            "wilson_locked": self.wilson_locked,
            "path_fraction": self.path_fraction,
            "path_wilson": self.path_wilson,
            "path_dependence": self.path_dependence,
            "zero_restored": self.zero_restored,
            "operational": self.operational,
        }


@dataclass(frozen=True, slots=True)
class LayerGate2Result:
    layer: str
    frozen_alpha: float
    frozen_interval: tuple[float, float]
    noise_floor: float
    epsilon_sym: float
    alpha_aggregates: tuple[AlphaAggregate, ...]
    observed_bracket: tuple[float, float] | None
    observed_alpha: float | None
    transition_width: float | None
    sharp: bool
    absolute_error: float | None
    relative_error: float | None
    interval_covers: bool
    multistability: bool
    negative_controls_pass: bool
    transition_exists: bool
    reasons: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.reasons

    def payload(self) -> dict[str, object]:
        return {
            "layer": self.layer,
            "frozen_alpha": self.frozen_alpha,
            "frozen_interval": self.frozen_interval,
            "noise_floor": self.noise_floor,
            "epsilon_sym": self.epsilon_sym,
            "alpha_aggregates": [item.payload() for item in self.alpha_aggregates],
            "observed_bracket": self.observed_bracket,
            "observed_alpha": self.observed_alpha,
            "transition_width": self.transition_width,
            "sharp": self.sharp,
            "absolute_error": self.absolute_error,
            "relative_error": self.relative_error,
            "interval_covers": self.interval_covers,
            "multistability": self.multistability,
            "negative_controls_pass": self.negative_controls_pass,
            "transition_exists": self.transition_exists,
            "reasons": self.reasons,
            "passed": self.passed,
        }


def _quantile(values: list[float], probability: float) -> float:
    if not values:
        raise ValueError("cannot calculate quantile of empty values")
    values.sort()
    position = (len(values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower
    return values[lower] * (1.0 - fraction) + values[upper] * fraction


def _wilson(successes: int, total: int) -> tuple[float, float]:
    if total <= 0:
        return (0.0, 0.0)
    z = 1.959963984540054
    proportion = successes / total
    denominator = 1.0 + z * z / total
    center = (proportion + z * z / (2.0 * total)) / denominator
    radius = (
        z
        * sqrt(proportion * (1.0 - proportion) / total + z * z / (4.0 * total * total))
        / denominator
    )
    return max(0.0, center - radius), min(1.0, center + radius)


def _slope(values: tuple[float, ...]) -> float:
    if len(values) < 2:
        return 0.0
    x_mean = (len(values) - 1) / 2.0
    y_mean = fmean(values)
    numerator = sum(
        (index - x_mean) * (value - y_mean) for index, value in enumerate(values)
    )
    denominator = sum((index - x_mean) ** 2 for index in range(len(values)))
    return numerator / denominator if denominator > 0 else 0.0


def _trace_digest(states: tuple[Vector, ...]) -> str:
    return hashlib.sha256(canonical_json(states).encode("utf-8")).hexdigest()


def _summary_from_states(
    layer: str,
    alpha: float,
    seed: int,
    initial_id: str,
    states: tuple[Vector, ...],
    projection: tuple[float, ...],
    operational: dict[str, float],
    tail_window: int,
) -> RunSummary:
    tail = states[-tail_window:]
    tail_projection = projection[-tail_window:]
    magnitudes = tuple(sqrt(dot(state, state)) for state in tail)
    third = max(1, tail_window // 3)
    preceding = magnitudes[:third]
    final = magnitudes[-third:]
    final_sign = 1.0 if tail_projection[-1] >= 0.0 else -1.0
    persistence = sum(
        1.0
        for value in tail_projection
        if (1.0 if value >= 0.0 else -1.0) == final_sign
    ) / len(tail_projection)
    return RunSummary(
        layer,
        alpha,
        seed,
        initial_id,
        states[-1],
        fmean(magnitudes),
        median(magnitudes),
        pstdev(magnitudes) ** 2,
        persistence,
        fmean(tail_projection),
        tail_projection[-1],
        _slope(magnitudes),
        fmean(preceding),
        fmean(final),
        _trace_digest(states),
        operational,
    )


def _run_reduced(
    model: ReducedModel,
    alpha: float,
    seed: int,
    initial_id: str,
    initial: Vector,
    horizon: int,
    noise_sd: float,
    tail_window: int,
) -> RunSummary:
    trajectory = model.simulate(
        initial,
        alpha,
        horizon,
        seed,
        noise_sd,
        magnitude=max(abs(item) for item in initial),
        direction_id=initial_id,
    )
    projection = tuple(dot(model.c, state) for state in trajectory.states)
    return _summary_from_states(
        "R", alpha, seed, initial_id, trajectory.states, projection, {}, tail_window
    )


def _metrics_payload(
    metrics: tuple[OperationalMetrics, ...], tail_window: int
) -> dict[str, float]:
    selected = metrics[-tail_window:]
    if not selected:
        return {}
    fields = {
        "accepted": tuple(item.accepted_a + item.accepted_b for item in selected),
        "served_demand": tuple(item.served_a + item.served_b for item in selected),
        "wait": tuple((item.wait_a + item.wait_b) / 2.0 for item in selected),
        "service_inequality": tuple(item.service_inequality for item in selected),
        "courier_opportunity_imbalance": tuple(
            abs(item.courier_opportunity_a - item.courier_opportunity_b)
            for item in selected
        ),
        "merchant_utilization": tuple(
            (item.utilization_a + item.utilization_b) / 2.0 for item in selected
        ),
    }
    return {key: fmean(values) for key, values in fields.items()}


def _run_mechanism(
    model: DeliveryMechanism,
    alpha: float,
    seed: int,
    initial_id: str,
    initial: Vector,
    horizon: int,
    noise_sd: float,
    tail_window: int,
) -> RunSummary:
    run: MechanismRun = model.simulate(initial, alpha, horizon, seed, noise_sd)
    weights = _float_list(
        model.parameters["service_score_weights"], "service_score_weights"
    )
    projection = tuple(
        sum(weight * value for weight, value in zip(weights, state, strict=True))
        for state in run.observations
    )
    return _summary_from_states(
        "M",
        alpha,
        seed,
        initial_id,
        run.observations,
        projection,
        _metrics_payload(run.metrics, tail_window),
        tail_window,
    )


def verify_frozen_inputs(package_root: Path, store: ArtifactStore) -> dict[str, object]:
    report = package_root / "reports" / "FROZEN_THRESHOLD_PREDICTION.md"
    if not report.is_file():
        raise ResearchGateError("FROZEN_INPUT_MISMATCH", "frozen report is missing")
    report_hash = hashlib.sha256(report.read_bytes()).hexdigest()
    if report_hash != FROZEN_REPORT_SHA256:
        raise ResearchGateError(
            "FROZEN_INPUT_MISMATCH", "frozen report SHA-256 changed"
        )
    payload, artifact = store.read_json(
        "confirmatory",
        "threshold/frozen-prediction-v1.json",
        expected_sha256=FROZEN_THRESHOLD_SHA256,
    )
    if payload.get("status") != "PASS":
        raise ResearchGateError(
            "FROZEN_INPUT_MISMATCH", "frozen Gate 1 status is not PASS"
        )
    predictions = payload.get("predictions")
    if not isinstance(predictions, dict):
        raise ResearchGateError(
            "FROZEN_INPUT_MISMATCH", "frozen predictions are missing"
        )
    layer_r = predictions.get("layer_r")
    layer_m = predictions.get("layer_m")
    if not isinstance(layer_r, dict) or not isinstance(layer_m, dict):
        raise ResearchGateError(
            "FROZEN_INPUT_MISMATCH", "layer predictions are malformed"
        )
    checks = (
        (layer_r.get("predicted_alpha_c"), FROZEN_R_ALPHA),
        (layer_r.get("alpha_c_ci95"), list(FROZEN_R_INTERVAL)),
        (layer_m.get("predicted_alpha_c"), FROZEN_M_ALPHA),
        (layer_m.get("alpha_c_ci95"), list(FROZEN_M_INTERVAL)),
    )
    for observed, expected in checks:
        if isinstance(expected, list):
            valid = (
                isinstance(observed, list)
                and len(observed) == len(expected)
                and all(
                    isclose(float(actual), float(target), rel_tol=0.0, abs_tol=1e-12)
                    for actual, target in zip(observed, expected, strict=True)
                )
            )
        else:
            valid = isinstance(observed, (float, int)) and isclose(
                float(observed), expected, rel_tol=0.0, abs_tol=1e-12
            )
        if not valid:
            raise ResearchGateError(
                "FROZEN_INPUT_MISMATCH", f"expected {expected}, got {observed}"
            )
    return {
        "report_sha256": report_hash,
        "threshold_sha256": artifact.sha256,
        "threshold_content_digest": artifact.content_digest,
        "layer_r": {"alpha": FROZEN_R_ALPHA, "interval": FROZEN_R_INTERVAL},
        "layer_m": {"alpha": FROZEN_M_ALPHA, "interval": FROZEN_M_INTERVAL},
    }


def _classify(summary: RunSummary, epsilon: float) -> str:
    if not all(
        isfinite(value)
        for value in (summary.imbalance_mean, summary.slope, summary.final_third_mean)
    ):
        return "AMBIGUOUS"
    if (
        summary.imbalance_mean <= epsilon
        and summary.slope <= 0.0
        and summary.final_third_mean <= summary.preceding_third_mean
    ):
        return "RESTORED"
    if (
        summary.imbalance_mean > epsilon
        and summary.sign_persistence >= 0.90
        and abs(summary.final_third_mean - summary.preceding_third_mean)
        <= 0.25 * epsilon + 0.01
    ):
        return "LOCKED"
    if summary.imbalance_mean > epsilon and summary.sign_persistence < 0.90:
        return "NOISY_SWITCHING"
    return "AMBIGUOUS"


def _bootstrap_difference(
    values: tuple[float, ...], seed: int, samples: int = 1000
) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    estimates = [
        fmean(values[rng.randrange(len(values))] for _ in range(len(values)))
        for _ in range(samples)
    ]
    return _quantile(estimates, 0.025), _quantile(estimates, 0.975)


def _aggregate_alpha(
    alpha: float,
    multiplier: float,
    records: tuple[RunSummary, ...],
    epsilon: float,
    seed_count: int,
) -> AlphaAggregate:
    classified = tuple(
        replace(record, classification=_classify(record, epsilon)) for record in records
    )
    by_key = {(item.seed, item.initial_id): item for item in classified}
    pair_labels: list[str] = []
    path_differences: list[float] = []
    for seed in range(21000, 21000 + seed_count):
        positive = by_key.get((seed, "positive"))
        negative = by_key.get((seed, "negative"))
        if positive is None or negative is None:
            pair_labels.append("AMBIGUOUS")
            continue
        if positive.classification == negative.classification == "RESTORED":
            pair_labels.append("RESTORED")
        elif positive.classification == negative.classification == "LOCKED":
            pair_labels.append("LOCKED")
        else:
            pair_labels.append("AMBIGUOUS")
        if (
            positive.classification == negative.classification == "LOCKED"
            and positive.projection_final * negative.projection_final < 0.0
        ):
            path_differences.append(positive.projection_mean - negative.projection_mean)
    restored = sum(label == "RESTORED" for label in pair_labels)
    locked = sum(label == "LOCKED" for label in pair_labels)
    wr = _wilson(restored, seed_count)
    wl = _wilson(locked, seed_count)
    path_fraction = len(path_differences) / seed_count
    path_interval = _wilson(len(path_differences), seed_count)
    path_ci = _bootstrap_difference(
        tuple(path_differences), int(alpha * 100000) + 42000
    )
    path = path_fraction >= 0.80 and path_interval[0] > 0.50 and path_ci[0] > 0.0
    robust_restored = restored / seed_count >= 0.80 and wr[0] > 0.50
    robust_locked = locked / seed_count >= 0.80 and wl[0] > 0.50 and path
    zero_records = [item for item in classified if item.initial_id == "zero"]
    zero_restored = (
        sum(item.classification == "RESTORED" for item in zero_records)
        / max(len(zero_records), 1)
        >= 0.80
    )
    if robust_restored:
        label = "ROBUST_RESTORED"
    elif robust_locked:
        label = "ROBUST_LOCKED"
    else:
        label = "UNRESOLVED"
    operational: dict[str, float] = {}
    operational_values = [item.operational for item in classified if item.operational]
    if operational_values:
        for key in operational_values[0]:
            operational[key] = fmean(item[key] for item in operational_values)
    return AlphaAggregate(
        alpha,
        multiplier,
        epsilon,
        label,
        restored,
        locked,
        seed_count,
        wr,
        wl,
        path_fraction,
        path_interval,
        path,
        zero_restored,
        operational,
        classified,
    )


def _noise_floor(records: tuple[RunSummary, ...]) -> float:
    values = [item.imbalance_mean for item in records if item.alpha == 0.0]
    if not values:
        raise ResearchGateError(
            "NEGATIVE_CONTROL_FAILED", "alpha=0 records are missing"
        )
    return median(values)


def _transition(
    aggregates: tuple[AlphaAggregate, ...],
) -> tuple[tuple[float, float] | None, bool]:
    ordered = sorted(
        (
            item
            for item in aggregates
            if item.robust_label in {"ROBUST_RESTORED", "ROBUST_LOCKED"}
        ),
        key=lambda item: item.alpha,
    )
    lower = [item for item in ordered if item.robust_label == "ROBUST_RESTORED"]
    upper = [item for item in ordered if item.robust_label == "ROBUST_LOCKED"]
    if not lower or not upper:
        return None, False
    lower_item = max(lower, key=lambda item: item.alpha)
    higher_locked = [item for item in upper if item.alpha > lower_item.alpha]
    if not higher_locked:
        return None, False
    upper_item = min(higher_locked, key=lambda item: item.alpha)
    for item in ordered:
        if item.alpha < lower_item.alpha and item.robust_label == "ROBUST_LOCKED":
            return None, False
        if item.alpha > upper_item.alpha and item.robust_label == "ROBUST_RESTORED":
            return None, False
    return (lower_item.alpha, upper_item.alpha), True


def _layer_validation(
    layer: str,
    model: ReducedModel | DeliveryMechanism,
    frozen_alpha: float,
    frozen_interval: tuple[float, float],
    validation: dict[str, object],
    identification: dict[str, object],
    layer_noise_sd: float,
    store: ArtifactStore,
) -> tuple[LayerGate2Result, tuple[StoredArtifact, ...]]:
    seeds = _int_list(validation["seeds"], "validation.seeds")
    horizon = int(_number(validation["horizon"], "validation.horizon"))
    tail_window = int(_number(validation["tail_window"], "validation.tail_window"))
    all_records: list[RunSummary] = []
    alpha_runs: list[tuple[float, float]] = [(0.0, 0.0)]
    coarse = _float_list(
        validation["coarse_alpha_multipliers"], "coarse_alpha_multipliers"
    )
    alpha_runs.extend((frozen_alpha * multiplier, multiplier) for multiplier in coarse)
    for alpha, _ in alpha_runs:
        for seed in seeds:
            for initial_id, initial in INITIALS:
                if layer == "R":
                    record = _run_reduced(
                        cast(ReducedModel, model),
                        alpha,
                        seed,
                        initial_id,
                        initial,
                        horizon,
                        layer_noise_sd,
                        tail_window,
                    )
                else:
                    record = _run_mechanism(
                        cast(DeliveryMechanism, model),
                        alpha,
                        seed,
                        initial_id,
                        initial,
                        horizon,
                        layer_noise_sd,
                        tail_window,
                    )
                all_records.append(record)
    noise_floor = _noise_floor(tuple(all_records))
    epsilon = max(0.02, 5.0 * noise_floor)
    coarse_aggregates = tuple(
        _aggregate_alpha(
            alpha,
            multiplier,
            tuple(item for item in all_records if item.alpha == alpha),
            epsilon,
            len(seeds),
        )
        for alpha, multiplier in alpha_runs
    )
    coarse_artifact = store.write_json(
        "confirmatory",
        f"gate2_long_horizon/{layer.lower()}-coarse.json",
        {
            "layer": layer,
            "stage": "coarse",
            "frozen_alpha": frozen_alpha,
            "frozen_interval": frozen_interval,
            "records": [item.payload() for item in all_records],
            "aggregates": [item.payload() for item in coarse_aggregates],
            "noise_floor": noise_floor,
            "epsilon_sym": epsilon,
        },
    )
    coarse_change = any(
        left.robust_label != right.robust_label
        for left, right in pairwise(coarse_aggregates)
    )
    fine_aggregates: tuple[AlphaAggregate, ...] = ()
    artifacts = [coarse_artifact]
    if coarse_change:
        fine_records: list[RunSummary] = []
        for multiplier in FINE_MULTIPLIERS:
            alpha = frozen_alpha * multiplier
            for seed in seeds:
                for initial_id, initial in INITIALS:
                    if layer == "R":
                        record = _run_reduced(
                            cast(ReducedModel, model),
                            alpha,
                            seed,
                            initial_id,
                            initial,
                            horizon,
                            layer_noise_sd,
                            tail_window,
                        )
                    else:
                        record = _run_mechanism(
                            cast(DeliveryMechanism, model),
                            alpha,
                            seed,
                            initial_id,
                            initial,
                            horizon,
                            layer_noise_sd,
                            tail_window,
                        )
                    fine_records.append(record)
        fine_aggregates = tuple(
            _aggregate_alpha(
                frozen_alpha * multiplier,
                multiplier,
                tuple(
                    item
                    for item in fine_records
                    if item.alpha == frozen_alpha * multiplier
                ),
                epsilon,
                len(seeds),
            )
            for multiplier in FINE_MULTIPLIERS
        )
        artifacts.append(
            store.write_json(
                "confirmatory",
                f"gate2_long_horizon/{layer.lower()}-fine.json",
                {
                    "layer": layer,
                    "stage": "fine",
                    "records": [item.payload() for item in fine_records],
                    "aggregates": [item.payload() for item in fine_aggregates],
                },
            )
        )
        all_records.extend(fine_records)
    aggregates = tuple(
        sorted(coarse_aggregates + fine_aggregates, key=lambda item: item.alpha)
    )
    bracket, transition_exists = _transition(aggregates)
    observed_alpha = (bracket[0] + bracket[1]) / 2.0 if bracket else None
    width = bracket[1] - bracket[0] if bracket else None
    sharp = bool(
        width is not None
        and observed_alpha is not None
        and width / observed_alpha <= 0.15
    )
    absolute = (
        abs(observed_alpha - frozen_alpha) if observed_alpha is not None else None
    )
    relative = (
        absolute / abs(observed_alpha)
        if absolute is not None and observed_alpha
        else None
    )
    interval_covers = bool(
        bracket
        and frozen_interval[0] <= bracket[1]
        and bracket[0] <= frozen_interval[1]
    )
    locked = [item for item in aggregates if item.robust_label == "ROBUST_LOCKED"]
    multistability = bool(locked and any(item.path_dependence for item in locked))
    negative = next((item for item in aggregates if item.multiplier == 0.40), None)
    negative_pass = bool(negative is not None and negative.zero_restored)
    reasons: list[str] = []
    if not transition_exists or not sharp:
        reasons.append("NO_SHARP_TRANSITION")
    if not multistability:
        reasons.append("PATH_DEPENDENCE_FAILED")
    if not negative_pass:
        reasons.append("NEGATIVE_CONTROL_FAILED")
    if relative is None or relative > 0.10 or not interval_covers:
        reasons.append("PREDICTION_ERROR")
    if not any(
        item.robust_label == "ROBUST_RESTORED" for item in aggregates
    ) or not any(item.robust_label == "ROBUST_LOCKED" for item in aggregates):
        reasons.append("SEED_ROBUSTNESS_FAILED")
    return (
        LayerGate2Result(
            layer,
            frozen_alpha,
            frozen_interval,
            noise_floor,
            epsilon,
            aggregates,
            bracket,
            observed_alpha,
            width,
            sharp,
            absolute,
            relative,
            interval_covers,
            multistability,
            negative_pass,
            transition_exists,
            tuple(dict.fromkeys(reasons)),
        ),
        tuple(artifacts),
    )


def run_gate2(
    package_root: Path, preregistration: Preregistration, store: ArtifactStore
) -> dict[str, object]:
    frozen = verify_frozen_inputs(package_root, store)
    gate_root = store.class_root("confirmatory") / "gate2_long_horizon"
    if gate_root.exists() and any(gate_root.iterdir()):
        raise ResearchGateError("GATE2_ARTIFACT_EXISTS", str(gate_root))
    payload = preregistration.payload
    validation = cast(dict[str, object], payload["validation"])
    identification = cast(dict[str, object], payload["identification"])
    layer_r = ReducedModel.from_config(cast(dict[str, object], payload["layer_r"]))
    layer_m = DeliveryMechanism.from_config(cast(dict[str, object], payload["layer_m"]))
    result_r, artifacts_r = _layer_validation(
        "R",
        layer_r,
        FROZEN_R_ALPHA,
        FROZEN_R_INTERVAL,
        validation,
        identification,
        _number(identification["layer_r_noise_sd"], "layer_r_noise_sd"),
        store,
    )
    result_m, artifacts_m = _layer_validation(
        "M",
        layer_m,
        FROZEN_M_ALPHA,
        FROZEN_M_INTERVAL,
        validation,
        identification,
        _number(identification["layer_m_noise_sd"], "layer_m_noise_sd"),
        store,
    )
    operational_pass = True
    if result_m.observed_bracket:
        lower, upper = result_m.observed_bracket
        low = next(item for item in result_m.alpha_aggregates if item.alpha == lower)
        high = next(item for item in result_m.alpha_aggregates if item.alpha == upper)
        operational_pass = high.operational.get(
            "service_inequality", 0.0
        ) > low.operational.get("service_inequality", 0.0)
    overall = (
        "PASS"
        if result_r.passed and result_m.passed and operational_pass
        else "PARTIAL"
        if result_r.passed or result_m.passed
        else "FAIL"
    )
    if not operational_pass and overall == "PASS":
        overall = "PARTIAL"
    summary = {
        "experiment_id": payload["experiment_id"],
        "stage": "gate2-long-horizon-validation",
        "artifact_class": "confirmatory",
        "status": overall,
        "frozen_inputs": frozen,
        "transition_definition": "research/level4/spatial_lockin/reports/GATE2_TRANSITION_DEFINITION.md",
        "generated_at": datetime.now(UTC).isoformat(),
        "layers": {"R": result_r.payload(), "M": result_m.payload()},
        "operational_correspondence": operational_pass,
        "gate3_eligibility": "YES"
        if overall == "PASS"
        else "CONDITIONAL"
        if overall == "PARTIAL"
        else "NO",
        "bulk_artifacts": [
            {
                "relative_path": item.relative_path,
                "sha256": item.sha256,
                "content_digest": item.content_digest,
            }
            for item in artifacts_r + artifacts_m
        ],
        "claim_limit": "No novelty or external-validity claim; Gate 3 not executed",
    }
    artifact = store.write_json(
        "confirmatory", "gate2_long_horizon/gate2_validation.json", summary
    )
    return {
        "status": overall,
        "gate3_eligibility": summary["gate3_eligibility"],
        "relative_path": artifact.relative_path,
        "sha256": artifact.sha256,
        "content_digest": artifact.content_digest,
        "layer_r": result_r.payload(),
        "layer_m": result_m.payload(),
        "operational_correspondence": operational_pass,
    }
