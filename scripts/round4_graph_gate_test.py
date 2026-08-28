from __future__ import annotations

import copy
import unittest
from typing import Any

from round4_graph_gate import (
    ACTIVE_GRAPH_PATH,
    GRAPH_PATH,
    Round4GraphError,
    _load,
    validate_graph,
)


class Round4GraphGateTests(unittest.TestCase):
    graph: dict[str, Any]
    active_graph: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = _load(GRAPH_PATH)
        cls.active_graph = _load(ACTIVE_GRAPH_PATH)

    def test_live_active_graph_passes(self) -> None:
        result = validate_graph(self.graph, self.active_graph)

        self.assertEqual(result["state"], "ACTIVE")
        self.assertEqual(result["task_count"], 38)
        self.assertEqual(result["workstream_count"], 6)
        self.assertEqual(result["external_gate_count"], 15)
        self.assertEqual(result["human_approval_count"], 12)
        self.assertEqual(result["conditional_task_count"], 3)
        self.assertEqual(result["closure_classification_count"], 11)
        self.assertEqual(result["preservation_lane_count"], 11)
        self.assertEqual(result["replacement_provider_gate_count"], 1)

    def test_replacement_provider_gate_representation_is_frozen(self) -> None:
        mutated = copy.deepcopy(self.graph)
        mutated["replacement_provider_gates"][0]["execution_outcome"]["overall"] = "PASS"

        with self.assertRaisesRegex(
            Round4GraphError, "replacement provider gate representation drifted"
        ):
            validate_graph(mutated, self.active_graph)

    def test_active_replacement_provider_gate_must_match(self) -> None:
        active = copy.deepcopy(self.active_graph)
        active["replacement_provider_gates"][0]["canonical_sha256"] = "0" * 64

        with self.assertRaisesRegex(
            Round4GraphError, "active replacement provider gate representation drifted"
        ):
            validate_graph(self.graph, active)

    def test_prepared_graph_rejects_started_task(self) -> None:
        mutated = copy.deepcopy(self.graph)
        mutated["state"] = "PREPARED_NOT_STARTED"
        for task in mutated["tasks"]:
            task["status"] = "pending"
        mutated["tasks"][0]["status"] = "in_progress"
        inactive = copy.deepcopy(self.active_graph)
        inactive["tasks"] = [
            task for task in inactive["tasks"] if not task["id"].startswith("R4-")
        ]

        with self.assertRaisesRegex(Round4GraphError, "prepared task was started"):
            validate_graph(mutated, inactive)

    def test_missing_active_task_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.active_graph)
        mutated["tasks"] = [task for task in mutated["tasks"] if task["id"] != "R4-499"]

        with self.assertRaisesRegex(Round4GraphError, "task inventory is incomplete"):
            validate_graph(self.graph, mutated)

    def test_forward_dependency_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.graph)
        mutated["tasks"][1]["depends_on"] = ["R4-499"]

        with self.assertRaisesRegex(Round4GraphError, "missing or forward dependency"):
            validate_graph(mutated, self.active_graph)

    def test_round3_claim_promotion_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.graph)
        mutated["source_round"]["final_claim_counts"]["C-PASS"] = 1

        with self.assertRaisesRegex(Round4GraphError, "final claim counts drifted"):
            validate_graph(mutated, self.active_graph)

    def test_human_approval_gate_weakening_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.graph)
        target = next(task for task in mutated["tasks"] if task["id"] == "R4-436")
        target["human_approval"] = False
        active = copy.deepcopy(self.active_graph)
        active_target = next(task for task in active["tasks"] if task["id"] == "R4-436")
        active_target["human_approval"] = False

        with self.assertRaisesRegex(
            Round4GraphError, "human-approval gate inventory drifted"
        ):
            validate_graph(mutated, active)

    def test_missing_reclassified_lane_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.graph)
        del mutated["preserved_round3_reclassifications"]["provider_backed_travel"]

        with self.assertRaisesRegex(
            Round4GraphError, "reclassification inventory drifted"
        ):
            validate_graph(mutated, self.active_graph)

    def test_conditional_activation_boundary_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.graph)
        target = next(task for task in mutated["tasks"] if task["id"] == "R4-440")
        del target["activation_condition"]

        with self.assertRaisesRegex(
            Round4GraphError, "conditional activation boundary drifted"
        ):
            validate_graph(mutated, self.active_graph)

    def test_closure_classification_coverage_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.graph)
        mutated["closure_classifications"]["CORE_CLOSURE"].remove("R4-499")

        with self.assertRaisesRegex(
            Round4GraphError, "closure classifications drifted"
        ):
            validate_graph(mutated, self.active_graph)


if __name__ == "__main__":
    unittest.main()
