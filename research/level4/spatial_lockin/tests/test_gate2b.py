from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from research.level4.spatial_lockin.artifacts import ArtifactStore
from research.level4.spatial_lockin.gate2b import (
    CALIBRATION_PATH,
    _control_gate,
    _layer_assessment,
    _require_stage_pass,
    _write,
)
from research.level4.spatial_lockin.gate2b_protocol import load_gate2b_protocol
from research.level4.spatial_lockin.reason_codes import ResearchGateError
from research.level4.spatial_lockin.stochastic_equilibrium import (
    ClassifiedRun,
    aggregate_alpha,
    classify_states,
    observed_transition,
    select_coarse_bracket,
)

WEIGHTS = (1.0 / 3.0, 7.0 / 24.0, 3.0 / 8.0)


def _states(kind: str) -> tuple[tuple[float, float, float], ...]:
    if kind == "restored":
        return tuple(
            (0.0001 if index % 2 == 0 else -0.0001, 0.0, 0.0) for index in range(4801)
        )
    if kind == "locked_positive":
        return ((0.02, 0.02, 0.02),) * 4801
    if kind == "locked_negative":
        return ((-0.02, -0.02, -0.02),) * 4801
    return tuple(
        ((0.02, 0.02, 0.02) if index % 2 == 0 else (-0.02, -0.02, -0.02))
        for index in range(4801)
    )


class Gate2bTests(unittest.TestCase):
    package_root: Path
    restored: ClassifiedRun
    locked_positive: ClassifiedRun
    locked_negative: ClassifiedRun
    transitional: ClassifiedRun

    @classmethod
    def setUpClass(cls) -> None:
        cls.package_root = Path(__file__).resolve().parents[1]
        cls.restored = classify_states(
            "R", 0.0, 0.0, 1, "zero", _states("restored"), WEIGHTS
        )
        cls.locked_positive = classify_states(
            "R", 4.0, 1.4, 1, "positive", _states("locked_positive"), WEIGHTS
        )
        cls.locked_negative = classify_states(
            "R", 4.0, 1.4, 1, "negative", _states("locked_negative"), WEIGHTS
        )
        cls.transitional = classify_states(
            "R", 2.0, 1.0, 1, "zero", _states("transitional"), WEIGHTS
        )

    def test_frozen_protocol_binds_interval_overlap_as_diagnostic_only(self) -> None:
        protocol = load_gate2b_protocol(self.package_root)
        gate = protocol.section("threshold_gate")
        controls = protocol.section("synthetic_controls")
        self.assertEqual(gate["relative_prediction_error_max"], 0.01)
        self.assertEqual(gate["relative_transition_width_max"], 0.025)
        self.assertFalse(gate["identification_interval_overlap_is_pass_condition"])
        self.assertTrue(controls["strict_split"])
        self.assertFalse(controls["classifier_changes_after_holdout"])

    def test_classifier_detects_restored_locked_and_transitional_states(self) -> None:
        self.assertEqual(self.restored.label, "STOCHASTIC_RESTORED")
        self.assertEqual(self.locked_positive.label, "LOCKED")
        self.assertEqual(self.locked_negative.label, "LOCKED")
        self.assertEqual(self.transitional.label, "TRANSITIONAL")
        self.assertLess(self.restored.statistics.covariance_trace, 0.000025)
        self.assertGreater(self.transitional.statistics.covariance_trace, 0.001)

    def test_drift_equivalence_rejects_a_centered_slow_trend(self) -> None:
        states = tuple(
            (0.0, 0.0, 0.0)
            if index < 3001
            else (-0.004 + 0.008 * (index - 3001) / 1799.0, 0.0, 0.0)
            for index in range(4801)
        )
        result = classify_states("R", 0.0, 0.0, 1, "zero", states, WEIGHTS)
        self.assertEqual(result.label, "TRANSITIONAL")
        self.assertGreater(result.statistics.cumulative_drift, 0.002)
        self.assertLess(abs(result.statistics.coordinate_means[0]), 1e-12)

    def test_aggregate_uses_frozen_48_of_64_pair_rule(self) -> None:
        records: list[ClassifiedRun] = []
        for seed in range(64):
            if seed < 48:
                positive = replace(
                    self.restored, seed=seed, initial_id="positive", alpha=1.0
                )
                negative = replace(
                    self.restored, seed=seed, initial_id="negative", alpha=1.0
                )
            else:
                positive = replace(
                    self.transitional, seed=seed, initial_id="positive", alpha=1.0
                )
                negative = replace(
                    self.transitional, seed=seed, initial_id="negative", alpha=1.0
                )
            zero = replace(
                self.restored if seed < 58 else self.transitional,
                seed=seed,
                initial_id="zero",
                alpha=1.0,
            )
            records.extend((zero, positive, negative))
        aggregate = aggregate_alpha(tuple(records))
        self.assertEqual(aggregate.label, "ROBUST_RESTORED")
        self.assertEqual(aggregate.paired_restored_count, 48)
        self.assertGreater(aggregate.restored_wilson95[0], 0.60)
        self.assertEqual(aggregate.zero_restored_count, 58)
        self.assertGreater(aggregate.zero_restored_wilson95[0], 0.80)

    def test_transition_selection_is_deterministic_and_reversal_fails(self) -> None:
        restored_records = tuple(
            replace(
                self.restored,
                seed=seed,
                alpha=1.0,
                multiplier=0.9,
                initial_id=initial,
            )
            for seed in range(64)
            for initial in ("zero", "positive", "negative")
        )
        locked_records = tuple(
            replace(
                self.locked_positive if initial != "negative" else self.locked_negative,
                seed=seed,
                alpha=1.1,
                multiplier=1.1,
                initial_id=initial,
            )
            for seed in range(64)
            for initial in ("zero", "positive", "negative")
        )
        low = aggregate_alpha(restored_records)
        high = aggregate_alpha(locked_records)
        self.assertEqual(select_coarse_bracket((low, high)), (low, high))
        self.assertEqual(observed_transition((low, high)), (1.0, 1.1))
        reversal = replace(low, alpha=1.2)
        self.assertIsNone(observed_transition((low, high, reversal)))

    def test_independent_control_gate_requires_quality(self) -> None:
        seeds = tuple(range(256))
        stable = tuple(replace(self.restored, seed=seed) for seed in seeds)
        locked = tuple(
            replace(
                self.locked_positive if initial == "positive" else self.locked_negative,
                seed=seed,
                initial_id=initial,
            )
            for seed in seeds
            for initial in ("positive", "negative")
        )
        near = tuple(replace(self.transitional, seed=seed) for seed in seeds)
        result = _control_gate(stable, locked, near, seeds)
        self.assertEqual(result["status"], "PASS")

    def test_interval_nonoverlap_is_supplementary_and_does_not_fail_accuracy(
        self,
    ) -> None:
        protocol = load_gate2b_protocol(self.package_root)
        frozen = 2.60097908919399
        specifications = (
            (0.0, "restored"),
            (0.4, "restored"),
            (0.65, "restored"),
            (2.59 / frozen, "restored"),
            (2.595 / frozen, "locked"),
            (1.4, "locked"),
            (1.6, "locked"),
        )
        records: list[ClassifiedRun] = []
        for multiplier, label in specifications:
            alpha = frozen * multiplier
            for seed in range(64):
                if label == "restored":
                    positive = replace(
                        self.restored,
                        seed=seed,
                        alpha=alpha,
                        multiplier=multiplier,
                        initial_id="positive",
                    )
                    negative = replace(positive, initial_id="negative")
                    zero = replace(positive, initial_id="zero")
                else:
                    positive = replace(
                        self.locked_positive,
                        seed=seed,
                        alpha=alpha,
                        multiplier=multiplier,
                        initial_id="positive",
                    )
                    negative = replace(
                        self.locked_negative,
                        seed=seed,
                        alpha=alpha,
                        multiplier=multiplier,
                        initial_id="negative",
                    )
                    zero = replace(
                        self.transitional,
                        seed=seed,
                        alpha=alpha,
                        multiplier=multiplier,
                        initial_id="zero",
                    )
                records.extend((zero, positive, negative))
        assessment = _layer_assessment(protocol, "R", tuple(records))
        self.assertEqual(assessment["status"], "PASS")
        self.assertFalse(assessment["identification_interval_intersects_bracket"])
        relative_error = assessment["relative_prediction_error"]
        relative_width = assessment["relative_transition_width"]
        if not isinstance(relative_error, float) or not isinstance(
            relative_width, float
        ):
            self.fail("threshold metrics must be numeric")
        self.assertLess(relative_error, 0.01)
        self.assertLess(relative_width, 0.025)

    def test_holdout_prerequisite_failure_does_not_create_holdout_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ArtifactStore(Path(directory))
            with self.assertRaises(ResearchGateError) as context:
                _require_stage_pass(store, CALIBRATION_PATH, "fixture")
            self.assertEqual(context.exception.reason.code, "STAGE_ORDER_VIOLATION")
            holdout = store.resolve(
                "confirmatory",
                "gate2b_stochastic_equilibrium/controls/holdout/results.json",
            )
            self.assertFalse(holdout.exists())
            self.assertFalse(holdout.parent.exists())

    def test_gate2b_artifact_write_is_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ArtifactStore(Path(directory))
            path = "gate2b_stochastic_equilibrium/fixture/result.json"
            _write(store, path, {"status": "PASS"})
            with self.assertRaises(ResearchGateError) as context:
                _write(store, path, {"status": "FAIL"})
            self.assertEqual(context.exception.reason.code, "GATE2B_ARTIFACT_EXISTS")


if __name__ == "__main__":
    unittest.main()
