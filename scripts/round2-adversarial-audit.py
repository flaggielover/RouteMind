"""Static adversarial checks for the RouteMind Round 2 closure gate.

This is intentionally a small, deterministic review aid. It does not replace
Playwright, service tests, or human product review; it catches regressions in
the claims that are easiest to reintroduce while polishing the demo surface.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "TASK_GRAPH.yaml"
WEB_SOURCE = ROOT / "apps" / "web" / "src"


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)


def load_graph() -> dict:
    try:
        return json.loads(GRAPH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot parse {GRAPH}: {exc}")
        raise SystemExit(1) from exc


def check_evidence(graph: dict) -> list[str]:
    findings: list[str] = []
    passed = [task for task in graph.get("tasks", []) if task.get("status") == "passed"]
    for task in passed:
        for relative in task.get("evidence", []):
            path = ROOT / relative
            if not path.is_file():
                findings.append(f"{task.get('id')}: missing evidence {relative}")
            elif not path.read_text(encoding="utf-8").strip():
                findings.append(f"{task.get('id')}: empty evidence {relative}")
    return findings


def check_buttons() -> list[str]:
    findings: list[str] = []
    button_pattern = re.compile(r"<button\b(?P<attributes>.*?)>", re.DOTALL)
    for path in WEB_SOURCE.rglob("*.tsx"):
        text = path.read_text(encoding="utf-8")
        for match in button_pattern.finditer(text):
            attributes = match.group("attributes")
            if "onClick=" not in attributes and "disabled" not in attributes:
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{path.relative_to(ROOT)}:{line}: button has no action or disabled state")
    return findings


def check_truthful_surface() -> list[str]:
    findings: list[str] = []
    app = (WEB_SOURCE / "App.tsx").read_text(encoding="utf-8")
    forbidden_literals = (
        "92.4",
        "87.6",
        "Ari Singh",
        "RM-2043",
        "Thanks for using RouteMind.",
    )
    for literal in forbidden_literals:
        if literal in app:
            findings.append(f"apps/web/src/App.tsx: fabricated live-surface literal remains: {literal}")
    for path in WEB_SOURCE.rglob("*.tsx"):
        text = path.read_text(encoding="utf-8")
        for marker in ("console.log(", "TODO", "FIXME"):
            if marker in text:
                findings.append(f"{path.relative_to(ROOT)}: unsupported debug or unfinished marker: {marker}")
    live = (WEB_SOURCE / "data" / "liveSnapshot.ts").read_text(encoding="utf-8")
    if "Live unavailable:" not in live or "emptySnapshot(\"live\"" not in live:
        findings.append("live snapshot does not expose an explicit unavailable state")
    return findings


def main() -> int:
    graph = load_graph()
    findings = check_evidence(graph) + check_buttons() + check_truthful_surface()
    if findings:
        for finding in findings:
            fail(finding)
        return 1
    passed = sum(task.get("status") == "passed" for task in graph.get("tasks", []))
    print(f"PASS: {passed} passed task evidence paths are present and non-empty")
    print("PASS: every web button has an action handler or explicit disabled state")
    print("PASS: live role surfaces contain no known fabricated demo literals or debug markers")
    print("PASS: live source has an explicit unavailable-state boundary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
