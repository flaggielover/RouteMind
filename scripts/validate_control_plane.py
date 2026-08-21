from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "TASK_GRAPH.yaml"
ALLOWED_PRIORITIES = {"critical", "high", "medium", "low"}


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
        if task.get("status") in {"ready", "in_progress", "implemented", "validating", "passed"}:
            unmet = [dep for dep in dependencies if by_id.get(dep, {}).get("status") != "passed"]
            if unmet:
                errors.append(f"{task_id}: active state has unmet dependencies {unmet}")

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
