from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "docs" / "research" / "ROUND_4_TASK_GRAPH.yaml"
ACTIVE_GRAPH_PATH = ROOT / "TASK_GRAPH.yaml"
EXPECTED_IDS = [
    *[f"R4-{value}" for value in range(400, 410)],
    *[f"R4-{value}" for value in range(410, 414)],
    *[f"R4-{value}" for value in range(420, 425)],
    *[f"R4-{value}" for value in range(430, 441)],
    *[f"R4-{value}" for value in range(450, 454)],
    *[f"R4-{value}" for value in range(460, 463)],
    "R4-499",
]
EXPECTED_WORKSTREAMS = {
    "P": [f"R4-{value}" for value in range(400, 410)],
    "T": [f"R4-{value}" for value in range(410, 414)],
    "U": [f"R4-{value}" for value in range(420, 425)],
    "R": [f"R4-{value}" for value in range(430, 441)],
    "A": [f"R4-{value}" for value in range(450, 454)],
    "S": [f"R4-{value}" for value in range(460, 463)] + ["R4-499"],
}
EXPECTED_PRESERVATIONS = {
    "production_readiness",
    "provider_backed_travel",
    "identity_and_tenancy",
    "preferences_notifications_accessibility",
    "tracing_cost_and_incident_drills",
    "scheduled_twin_experiments",
    "broad_agent_evaluation",
    "li_lim_applicability",
    "ope_estimators_if_identifiable",
    "rads_outcome_evidence",
    "external_reproduction_and_thesis",
}
EXPECTED_CLOSURE_CLASSIFICATIONS = {
    "CORE_CLOSURE": {"R4-400", "R4-409", "R4-430", "R4-499"},
    "PRODUCTION": {"R4-401"},
    "SECURITY": {"R4-402", "R4-403", "R4-404", "R4-450", "R4-451"},
    "RELIABILITY": {"R4-405", "R4-406", "R4-408"},
    "PERFORMANCE": {"R4-407"},
    "DATA_GOVERNANCE": {"R4-420", "R4-438"},
    "FINAL_BENCHMARK": {"R4-434", "R4-435", "R4-439", "R4-452"},
    "PRODUCT_DEMO": {"R4-421", "R4-423", "R4-424"},
    "THESIS_DEFENSE": {"R4-461", "R4-462"},
    "DEFERRED_EXTERNAL": {
        "R4-410",
        "R4-411",
        "R4-412",
        "R4-413",
        "R4-422",
        "R4-431",
        "R4-432",
        "R4-433",
        "R4-436",
        "R4-460",
    },
    "OPTIONAL_STRETCH": {"R4-437", "R4-440", "R4-453"},
}
EXTERNAL_TASKS = {
    "R4-401",
    "R4-405",
    "R4-406",
    "R4-407",
    "R4-408",
    "R4-410",
    "R4-411",
    "R4-412",
    "R4-422",
    "R4-431",
    "R4-432",
    "R4-433",
    "R4-436",
    "R4-460",
    "R4-461",
}
HUMAN_APPROVAL_TASKS = {
    "R4-401",
    "R4-407",
    "R4-408",
    "R4-410",
    "R4-411",
    "R4-422",
    "R4-431",
    "R4-432",
    "R4-435",
    "R4-436",
    "R4-453",
    "R4-460",
}
CONDITIONAL_TASKS = {"R4-437", "R4-440", "R4-453"}
EXPECTED_CLOSURE_DEPENDENCIES = {
    "R4-409",
    "R4-413",
    "R4-424",
    "R4-433",
    "R4-436",
    "R4-439",
    "R4-452",
    "R4-460",
    "R4-462",
}


class Round4GraphError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Round4GraphError(f"cannot load graph: {path}") from exc
    if not isinstance(value, dict):
        raise Round4GraphError("graph root must be an object")
    return value


def validate_graph(
    graph: dict[str, Any], active_graph: dict[str, Any]
) -> dict[str, Any]:
    if graph.get("schema_version") != 1:
        raise Round4GraphError("Round 4 graph schema drifted")
    if graph.get("graph") != "RouteMind Round 4 Production and Thesis":
        raise Round4GraphError("Round 4 graph identity drifted")
    state = graph.get("state")
    if state not in {"PREPARED_NOT_STARTED", "ACTIVE", "CLOSED"}:
        raise Round4GraphError("Round 4 state is invalid")

    source = graph.get("source_round", {})
    if source.get("closure_task") != "R3-365":
        raise Round4GraphError("Round 3 closure lineage drifted")
    if source.get("final_claim_counts") != {
        "C-PASS": 0,
        "C-NO-NOVELTY": 2,
        "C-NO-CLAIM": 5,
        "C-DEFERRED": 0,
    }:
        raise Round4GraphError("Round 3 final claim counts drifted")
    if source.get("frozen_r3_325") != "E-PASS / X-PASS / S-FAIL / C-NO-CLAIM":
        raise Round4GraphError("R3-325 frozen outcome drifted")

    policy = graph.get("execution_policy", {})
    if set(policy) != {
        "all_tasks_start_pending",
        "promote_only_after_round3_closure",
        "external_evidence_required_for_external_gates",
        "human_approval_required_where_marked",
        "no_production_or_scientific_claim_from_preparation",
        "conditional_tasks_do_not_activate_without_their_recorded_condition",
    } or not all(value is True for value in policy.values()):
        raise Round4GraphError("Round 4 execution policy drifted")

    invariants = graph.get("architecture_invariants", [])
    required_invariant_terms = [
        "Java owns",
        "Python owns",
        "PostgreSQL",
        "LLM agents",
        "External provider",
    ]
    if not isinstance(invariants, list) or not all(
        any(term in invariant for invariant in invariants)
        for term in required_invariant_terms
    ):
        raise Round4GraphError("architecture invariants are incomplete")

    tasks = graph.get("tasks")
    if not isinstance(tasks, list):
        raise Round4GraphError("Round 4 tasks must be a list")
    ids = [task.get("id") for task in tasks]
    if ids != EXPECTED_IDS:
        raise Round4GraphError("Round 4 task identities or dependency order drifted")
    if len(set(ids)) != len(ids):
        raise Round4GraphError("Round 4 task identities are duplicated")

    active_tasks = {
        task.get("id"): task
        for task in active_graph.get("tasks", [])
        if task.get("id") in EXPECTED_IDS
    }
    if state == "PREPARED_NOT_STARTED" and active_tasks:
        raise Round4GraphError("prepared Round 4 task was activated in TASK_GRAPH.yaml")
    if state != "PREPARED_NOT_STARTED" and set(active_tasks) != set(EXPECTED_IDS):
        raise Round4GraphError("active Round 4 task inventory is incomplete")

    seen: set[str] = set()
    for task in tasks:
        task_id = task["id"]
        required_fields = {
            "id",
            "title",
            "workstream",
            "priority",
            "classification",
            "depends_on",
            "status",
            "external_gate",
            "human_approval",
            "acceptance",
            "evidence",
            "round3_lineage",
        }
        if not required_fields.issubset(task):
            raise Round4GraphError(f"task fields are incomplete: {task_id}")
        if state == "PREPARED_NOT_STARTED" and task["status"] != "pending":
            raise Round4GraphError(f"prepared task was started: {task_id}")
        if state == "ACTIVE" and task["status"] not in {
            "pending",
            "ready",
            "in_progress",
            "implemented",
            "validating",
            "passed",
            "failed",
            "blocked",
            "deferred_external",
        }:
            raise Round4GraphError(f"active task status is invalid: {task_id}")
        if state == "CLOSED" and task["status"] not in {"passed", "deferred_external"}:
            raise Round4GraphError(f"closed task is not terminal: {task_id}")
        if task["priority"] not in {"critical", "high", "medium", "low"}:
            raise Round4GraphError(f"task priority is invalid: {task_id}")
        if not isinstance(task["external_gate"], bool) or not isinstance(
            task["human_approval"], bool
        ):
            raise Round4GraphError(f"task gate types are invalid: {task_id}")
        dependencies = task["depends_on"]
        if not isinstance(dependencies, list) or any(
            dependency not in seen for dependency in dependencies
        ):
            raise Round4GraphError(f"task has missing or forward dependency: {task_id}")
        if not isinstance(task["acceptance"], list) or len(task["acceptance"]) < 2:
            raise Round4GraphError(f"task acceptance is incomplete: {task_id}")
        if not isinstance(task["evidence"], list) or not task["evidence"]:
            raise Round4GraphError(f"task evidence is incomplete: {task_id}")
        if not isinstance(task["round3_lineage"], list) or not task["round3_lineage"]:
            raise Round4GraphError(f"task Round 3 lineage is incomplete: {task_id}")
        if (task_id in CONDITIONAL_TASKS) != bool(task.get("activation_condition")):
            raise Round4GraphError(
                f"conditional activation boundary drifted: {task_id}"
            )
        if state != "PREPARED_NOT_STARTED":
            active_task = active_tasks[task_id]
            mirrored_fields = {
                "title",
                "workstream",
                "priority",
                "classification",
                "depends_on",
                "status",
                "external_gate",
                "human_approval",
                "acceptance",
                "evidence",
                "round3_lineage",
            }
            if any(
                active_task.get(field) != task.get(field) for field in mirrored_fields
            ):
                raise Round4GraphError(f"active task contract drifted: {task_id}")
        seen.add(task_id)

    if state == "ACTIVE" and tasks[0]["status"] == "pending":
        raise Round4GraphError("active Round 4 has no promoted control-plane task")
    if state == "CLOSED" and tasks[-1]["status"] != "passed":
        raise Round4GraphError("Round 4 closure task is not passed")

    actual_external = {task["id"] for task in tasks if task["external_gate"]}
    if actual_external != EXTERNAL_TASKS:
        raise Round4GraphError("external gate inventory drifted")
    actual_human = {task["id"] for task in tasks if task["human_approval"]}
    if actual_human != HUMAN_APPROVAL_TASKS:
        raise Round4GraphError("human-approval gate inventory drifted")

    workstreams = graph.get("workstreams")
    if not isinstance(workstreams, list):
        raise Round4GraphError("Round 4 workstreams must be a list")
    actual_workstreams = {item.get("id"): item.get("tasks") for item in workstreams}
    if actual_workstreams != EXPECTED_WORKSTREAMS:
        raise Round4GraphError("Round 4 workstream inventory drifted")
    if Counter(task_id for item in workstreams for task_id in item["tasks"]) != Counter(
        ids
    ):
        raise Round4GraphError("Round 4 workstream coverage drifted")
    if any(task["workstream"] not in EXPECTED_WORKSTREAMS for task in tasks):
        raise Round4GraphError("task references an unknown workstream")
    if any(
        task["id"] not in EXPECTED_WORKSTREAMS[task["workstream"]] for task in tasks
    ):
        raise Round4GraphError("task workstream assignment drifted")

    closure_classifications = graph.get("closure_classifications")
    if (
        not isinstance(closure_classifications, dict)
        or {key: set(value) for key, value in closure_classifications.items()}
        != EXPECTED_CLOSURE_CLASSIFICATIONS
    ):
        raise Round4GraphError("Round 4 closure classifications drifted")
    classified_ids = [
        task_id for task_ids in closure_classifications.values() for task_id in task_ids
    ]
    if Counter(classified_ids) != Counter(EXPECTED_IDS):
        raise Round4GraphError("Round 4 closure classification coverage drifted")
    if state != "PREPARED_NOT_STARTED":
        classification_by_id = {
            task_id: classification
            for classification, task_ids in closure_classifications.items()
            for task_id in task_ids
        }
        if any(
            active_tasks[task_id].get("closure_classification")
            != classification_by_id[task_id]
            for task_id in EXPECTED_IDS
        ):
            raise Round4GraphError("active closure classification drifted")

    preserved = graph.get("preserved_round3_reclassifications")
    if not isinstance(preserved, dict) or set(preserved) != EXPECTED_PRESERVATIONS:
        raise Round4GraphError("Round 3 reclassification inventory drifted")
    if any(
        not isinstance(references, list)
        or not references
        or any(task_id not in ids for task_id in references)
        for references in preserved.values()
    ):
        raise Round4GraphError("Round 3 reclassification references are invalid")

    critical_spine = graph.get("critical_spine")
    if not isinstance(critical_spine, list) or len(set(critical_spine)) != len(
        critical_spine
    ):
        raise Round4GraphError("Round 4 critical spine is invalid")
    if critical_spine[0] != "R4-400" or critical_spine[-1] != "R4-499":
        raise Round4GraphError("Round 4 critical spine endpoints drifted")
    if any(task_id not in ids for task_id in critical_spine):
        raise Round4GraphError("Round 4 critical spine references an unknown task")

    closure = tasks[-1]
    if set(closure["depends_on"]) != EXPECTED_CLOSURE_DEPENDENCIES:
        raise Round4GraphError("Round 4 closure dependency lanes drifted")
    closure_rule = graph.get("closure_rule", "")
    if not all(task_id in closure_rule for task_id in CONDITIONAL_TASKS):
        raise Round4GraphError(
            "Round 4 conditional closure dispositions are incomplete"
        )

    return {
        "valid": True,
        "state": graph["state"],
        "task_count": len(tasks),
        "workstream_count": len(workstreams),
        "external_gate_count": len(actual_external),
        "human_approval_count": len(actual_human),
        "conditional_task_count": len(CONDITIONAL_TASKS),
        "closure_classification_count": len(closure_classifications),
        "preservation_lane_count": len(preserved),
    }


def main() -> int:
    try:
        result = validate_graph(_load(GRAPH_PATH), _load(ACTIVE_GRAPH_PATH))
    except Round4GraphError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
