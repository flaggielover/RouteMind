from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "TASK_GRAPH.yaml"
ALLOWED_PRIORITIES = {"critical", "high", "medium", "low"}
RESEARCH_CLASSIFICATIONS = {
    "CORE_RESEARCH",
    "RESEARCH_INFRASTRUCTURE",
    "PARALLEL_ENGINEERING",
    "ROUND_4_PRODUCTION",
    "DEFERRED",
    "REMOVE_FROM_ROUND_3_CRITICAL_PATH",
}
ENGINEERING_STATUSES = {
    "E-PENDING",
    "E-IN-PROGRESS",
    "E-PASS",
    "E-FAIL",
    "E-DEFERRED",
    "E-NOT-REQUIRED",
}
EXPERIMENT_STATUSES = {
    "X-PENDING",
    "X-IN-PROGRESS",
    "X-PASS",
    "X-FAIL",
    "X-DEFERRED",
    "X-NOT-REQUIRED",
}
STATISTICAL_STATUSES = {
    "S-PENDING",
    "S-IN-PROGRESS",
    "S-PASS",
    "S-FAIL",
    "S-DEFERRED",
    "S-NOT-APPLICABLE",
}
CLAIM_STATUSES = {
    "C-PENDING",
    "C-PASS",
    "C-NO-NOVELTY",
    "C-NO-CLAIM",
    "C-DEFERRED",
    "C-NOT-APPLICABLE",
}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)


def load_graph() -> dict:
    try:
        return json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot parse {GRAPH_PATH.name} as JSON-compatible YAML: {exc}")
        raise SystemExit(1) from exc


def validate(graph: dict) -> list[str]:
    errors: list[str] = []
    statuses = set(graph.get("statuses", []))
    tasks = graph.get("tasks")
    if graph.get("schema_version") != 1:
        errors.append("schema_version must equal 1")
    if not statuses:
        errors.append("statuses must be non-empty")
    if not isinstance(tasks, list) or not tasks:
        return errors + ["tasks must be a non-empty list"]

    ids = [task.get("id") for task in tasks]
    if any(not task_id for task_id in ids):
        errors.append("every task must have an id")
    if len(ids) != len(set(ids)):
        errors.append("task ids must be unique")
    known_ids = set(ids)
    by_id = {task["id"]: task for task in tasks if task.get("id")}

    for task in tasks:
        task_id = task.get("id", "<missing>")
        if not task.get("title"):
            errors.append(f"{task_id}: title is required")
        if task.get("priority") not in ALLOWED_PRIORITIES:
            errors.append(f"{task_id}: invalid priority {task.get('priority')!r}")
        if task.get("status") not in statuses:
            errors.append(f"{task_id}: invalid status {task.get('status')!r}")
        if not task.get("acceptance"):
            errors.append(f"{task_id}: acceptance must be non-empty")
        if not task.get("gates"):
            errors.append(f"{task_id}: gates must be non-empty")
        dependencies = task.get("depends_on", [])
        unknown = set(dependencies) - known_ids
        if unknown:
            errors.append(f"{task_id}: unknown dependencies {sorted(unknown)}")
        if task_id in dependencies:
            errors.append(f"{task_id}: task cannot depend on itself")
        if task.get("status") == "passed" and not task.get("evidence"):
            errors.append(f"{task_id}: passed tasks require evidence")
        if task.get("status") in {
            "ready",
            "in_progress",
            "implemented",
            "validating",
            "passed",
        }:
            unmet = [
                dep
                for dep in dependencies
                if not _dependency_satisfied(task, dep, by_id)
            ]
            if unmet:
                errors.append(f"{task_id}: active state has unmet dependencies {unmet}")
        if task.get("status") == "condition_not_met":
            if not task.get("activation_condition"):
                errors.append(f"{task_id}: condition_not_met requires activation_condition")
            evaluation = task.get("condition_evaluation")
            required = {
                "condition",
                "result",
                "evaluated_at_utc",
                "checkpoint",
                "evidence",
                "reason",
                "reactivation_rule",
            }
            if not isinstance(evaluation, dict) or not required.issubset(evaluation):
                errors.append(
                    f"{task_id}: condition_not_met requires a complete condition_evaluation"
                )
            elif (
                evaluation.get("result") != "CONDITION_NOT_MET"
                or not evaluation.get("evidence")
                or any(
                    not isinstance(evaluation.get(field), str)
                    or not evaluation[field].strip()
                    for field in required - {"evidence"}
                )
            ):
                errors.append(
                    f"{task_id}: condition_not_met evaluation values are invalid"
                )
        if str(task_id).startswith("R3-"):
            if task.get("classification") not in RESEARCH_CLASSIFICATIONS:
                errors.append(
                    f"{task_id}: invalid research classification {task.get('classification')!r}"
                )
            if not task.get("workstream"):
                errors.append(f"{task_id}: research workstream is required")
            scientific_fields = (
                ("engineering_status", ENGINEERING_STATUSES),
                ("experiment_status", EXPERIMENT_STATUSES),
                ("statistical_status", STATISTICAL_STATUSES),
                ("claim_status", CLAIM_STATUSES),
            )
            for field_name, allowed in scientific_fields:
                if task.get(field_name) not in allowed:
                    errors.append(
                        f"{task_id}: invalid {field_name} {task.get(field_name)!r}"
                    )
            if task.get("status") == "passed":
                if task.get("engineering_status") not in {"E-PASS", "E-NOT-REQUIRED"}:
                    errors.append(f"{task_id}: passed research task requires a final E gate")
                if task.get("experiment_status") in {"X-PENDING", "X-IN-PROGRESS"}:
                    errors.append(f"{task_id}: passed research task cannot have an open X gate")
                if task.get("statistical_status") in {"S-PENDING", "S-IN-PROGRESS"}:
                    errors.append(f"{task_id}: passed research task cannot have an open S gate")
                if task.get("claim_status") == "C-PENDING":
                    errors.append(f"{task_id}: passed research task cannot have an open C gate")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            errors.append(f"dependency cycle includes {task_id}")
            return
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in by_id[task_id].get("depends_on", []):
            if dependency in by_id:
                visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in by_id:
        visit(task_id)

    return errors


def _dependency_satisfied(task: dict, dependency: str, by_id: dict[str, dict]) -> bool:
    selected = by_id.get(dependency, {})
    if selected.get("status") == "passed":
        return True
    scopes = task.get("dependency_scope", {})
    if not isinstance(scopes, dict) or scopes.get(dependency) != "local_preparation":
        return False
    return (
        selected.get("external_gate") is True
        and selected.get("local_preparation_status") == "passed"
    )


def main() -> int:
    errors = validate(load_graph())
    if errors:
        for error in errors:
            fail(error)
        return 1
    print("PASS: task graph schema, dependencies, states, and evidence rules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
