from __future__ import annotations

import ast
from pathlib import Path

PACKAGE_ROOT = Path(__file__).parents[1] / "src" / "routemind_compute"
LAYER_RANK = {"domain": 0, "application": 1, "api": 2, "infrastructure": 2}


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_domain_uses_only_the_standard_library() -> None:
    domain_files = (PACKAGE_ROOT / "domain").glob("*.py")
    imports = set().union(*(imported_modules(path) for path in domain_files))
    allowed_roots = {"__future__", "dataclasses", "typing"}

    assert {module.split(".")[0] for module in imports} <= allowed_roots


def test_layers_do_not_depend_inward_on_outer_layers() -> None:
    violations: list[str] = []
    for layer, rank in LAYER_RANK.items():
        for path in (PACKAGE_ROOT / layer).glob("*.py"):
            for module in imported_modules(path):
                prefix = "routemind_compute."
                if not module.startswith(prefix):
                    continue
                imported_layer = module.removeprefix(prefix).split(".")[0]
                if imported_layer in LAYER_RANK and LAYER_RANK[imported_layer] > rank:
                    violations.append(f"{path.name}: {layer} -> {imported_layer}")

    assert violations == []
