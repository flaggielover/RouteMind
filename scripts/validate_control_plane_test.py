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

    def test_local_preparation_scope_can_satisfy_an_external_dependency(self) -> None:
        graph = {
            "schema_version": 1,
            "statuses": ["pending", "blocked", "passed", "condition_not_met"],
            "tasks": [
                {
                    "id": "R4-405",
                    "title": "external telemetry",
                    "priority": "high",
                    "status": "blocked",
                    "depends_on": [],
                    "acceptance": ["target evidence"],
                    "gates": ["external"],
                    "evidence": ["evidence/r4-405.md"],
                    "external_gate": True,
                    "local_preparation_status": "passed",
                },
                {
                    "id": "R4-430",
                    "title": "scheduler",
                    "priority": "critical",
                    "status": "passed",
                    "depends_on": ["R4-405"],
                    "dependency_scope": {"R4-405": "local_preparation"},
                    "acceptance": ["bounded scheduler"],
                    "gates": ["local"],
                    "evidence": ["evidence/r4-430.md"],
                },
            ],
        }
        self.assertEqual(validate_control_plane.validate(graph), [])

    def test_condition_not_met_requires_an_evaluation_record(self) -> None:
        graph = valid_graph()
        graph["statuses"].append("condition_not_met")
        task = graph["tasks"][1]
        task["id"] = "R4-453"
        task["status"] = "condition_not_met"
        task["activation_condition"] = "read-only evaluation passes"
        self.assertTrue(
            any(
                "condition_not_met requires a complete" in error
                for error in validate_control_plane.validate(graph)
            )
        )


if __name__ == "__main__":
    unittest.main()
