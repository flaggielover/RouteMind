from __future__ import annotations

import copy
import unittest

import validate_control_plane


def valid_graph() -> dict:
    return {
        "schema_version": 1,
        "statuses": ["pending", "in_progress", "passed"],
        "tasks": [
            {
                "id": "RM-001",
                "title": "foundation",
                "priority": "critical",
                "status": "passed",
                "depends_on": [],
                "acceptance": ["foundation exists"],
                "gates": ["L1"],
                "evidence": ["evidence/foundation.md"],
            },
            {
                "id": "R3-300",
                "title": "research control",
                "priority": "critical",
                "status": "in_progress",
                "depends_on": ["RM-001"],
                "acceptance": ["scientific gates exist"],
                "gates": ["L1-research"],
                "evidence": [],
                "classification": "RESEARCH_INFRASTRUCTURE",
                "workstream": "A",
                "engineering_status": "E-IN-PROGRESS",
                "experiment_status": "X-NOT-REQUIRED",
                "statistical_status": "S-NOT-APPLICABLE",
                "claim_status": "C-NOT-APPLICABLE",
            },
        ],
    }


class ScientificTaskValidationTests(unittest.TestCase):
    def test_accepts_four_dimensional_research_state(self) -> None:
        self.assertEqual(validate_control_plane.validate(valid_graph()), [])

    def test_rejects_missing_scientific_gate(self) -> None:
        graph = valid_graph()
        del graph["tasks"][1]["claim_status"]

        self.assertIn(
            "R3-300: invalid claim_status None",
            validate_control_plane.validate(graph),
        )

    def test_rejects_passed_task_with_open_scientific_gate(self) -> None:
        graph = copy.deepcopy(valid_graph())
        task = graph["tasks"][1]
        task["status"] = "passed"
        task["engineering_status"] = "E-PASS"
        task["experiment_status"] = "X-PENDING"

        self.assertIn(
            "R3-300: passed research task cannot have an open X gate",
            validate_control_plane.validate(graph),
        )


if __name__ == "__main__":
    unittest.main()
