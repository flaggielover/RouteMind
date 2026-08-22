from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from staged_release import ReleaseStage, StageObservation, StagePlan, evaluate_stage


def stage(stage_id: str, traffic_bps: int) -> ReleaseStage:
    return ReleaseStage(stage_id, traffic_bps, 100, 60, 500, 400, 300, ("business-api", "compute-api"))


def plan() -> StagePlan:
    return StagePlan("a" * 64, "b" * 64, "c" * 64, "policy-v1", (stage("canary", 100), stage("full", 10_000)))


def observation(stage_id: str = "canary", **overrides: object) -> StageObservation:
    values: dict[str, object] = {
        "stage_id": stage_id,
        "samples": 100,
        "soak_seconds": 60,
        "error_bps": 10,
        "regression_bps": 10,
        "disagreement_bps": 10,
        "health_checks": (("compute-api", True), ("business-api", True)),
        "rollback_ready": True,
    }
    values.update(overrides)
    return StageObservation(**values)  # type: ignore[arg-type]


class StagedReleaseTests(unittest.TestCase):
    def test_plan_is_content_addressed_and_order_normalized(self) -> None:
        value = plan()
        reordered = StagePlan(value.active_release_digest, value.candidate_release_digest, value.rollback_package_digest, value.policy_version, tuple(reversed(value.stages)))
        self.assertEqual(value.digest, reordered.digest)
        with self.assertRaisesRegex(ValueError, "final stage"):
            StagePlan("a" * 64, "b" * 64, "c" * 64, "policy-v1", (stage("canary", 100), stage("partial", 500)))
        with self.assertRaisesRegex(ValueError, "strictly"):
            StagePlan("a" * 64, "b" * 64, "c" * 64, "policy-v1", (stage("first", 100), stage("second", 100), stage("full", 10_000)))

    def test_safe_complete_stage_promotes_only_to_next_stage(self) -> None:
        result = evaluate_stage(plan(), observation())
        self.assertEqual(result.decision, "promote")
        self.assertEqual(result.next_stage_id, "full")
        self.assertEqual(result.reasons, ("advance_to:full",))
        self.assertEqual(result.digest, evaluate_stage(plan(), observation()).digest)

    def test_samples_or_soak_incomplete_holds(self) -> None:
        result = evaluate_stage(plan(), observation(samples=99, soak_seconds=59))
        self.assertEqual(result.decision, "hold")
        self.assertEqual(result.reasons, ("samples_incomplete:99<100", "soak_incomplete:59<60"))

    def test_safety_failures_rollback_even_when_observation_is_incomplete(self) -> None:
        result = evaluate_stage(
            plan(),
            observation(samples=0, soak_seconds=0, rollback_ready=False, error_bps=500, health_checks=(("business-api", False),)),
        )
        self.assertEqual(result.decision, "rollback")
        self.assertIsNone(result.next_stage_id)
        self.assertEqual(
            result.reasons,
            (
                "rollback_not_ready",
                "health_check_unhealthy:business-api",
                "health_check_missing:compute-api",
                "error_threshold:500>=500",
            ),
        )

    def test_unknown_stage_and_missing_health_are_blocked_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = list(root.iterdir())
            result = evaluate_stage(plan(), observation("unknown"))
            self.assertEqual(result.decision, "rollback")
            self.assertEqual(result.reasons, ("unknown_stage:unknown",))
            self.assertEqual(before, list(root.iterdir()))
        with self.assertRaisesRegex(ValueError, "lowercase"):
            StagePlan("A" * 64, "b" * 64, "c" * 64, "policy-v1", (stage("full", 10_000),))


if __name__ == "__main__":
    unittest.main()
