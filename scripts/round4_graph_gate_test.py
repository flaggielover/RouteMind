from __future__ import annotations

import copy
import unittest

from round4_graph_gate import (
    ACTIVE_GRAPH_PATH,
    GRAPH_PATH,
    Round4GraphError,
    _load,
    validate_graph,
)


class Round4GraphGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = _load(GRAPH_PATH)
        cls.active_graph = _load(ACTIVE_GRAPH_PATH)

    def test_live_prepared_graph_passes(self) -> None:
        result = validate_graph(self.graph, self.active_graph)

        self.assertEqual(result["state"], "PREPARED_NOT_STARTED")
        self.assertEqual(result["task_count"], 38)
        self.assertEqual(result["workstream_count"], 6)
        self.assertEqual(result["external_gate_count"], 15)
        self.assertEqual(result["human_approval_count"], 12)
        self.assertEqual(result["conditional_task_count"], 3)
        self.assertEqual(result["preservation_lane_count"], 11)

    def test_started_task_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.graph)
        mutated["tasks"][0]["status"] = "in_progress"

        with self.assertRaisesRegex(Round4GraphError, "prepared task was started"):
            validate_graph(mutated, self.active_graph)

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

        with self.assertRaisesRegex(Round4GraphError, "human-approval gate inventory drifted"):
            validate_graph(mutated, self.active_graph)

    def test_missing_reclassified_lane_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.graph)
        del mutated["preserved_round3_reclassifications"]["provider_backed_travel"]

        with self.assertRaisesRegex(Round4GraphError, "reclassification inventory drifted"):
            validate_graph(mutated, self.active_graph)

    def test_conditional_activation_boundary_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.graph)
        target = next(task for task in mutated["tasks"] if task["id"] == "R4-440")
        del target["activation_condition"]

        with self.assertRaisesRegex(Round4GraphError, "conditional activation boundary drifted"):
            validate_graph(mutated, self.active_graph)


if __name__ == "__main__":
    unittest.main()
