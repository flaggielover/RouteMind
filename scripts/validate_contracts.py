from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).parents[1]
CONTRACTS = ROOT / "contracts"


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def main() -> None:
    manifest = load_json(CONTRACTS / "manifest.json")
    checked = 0
    for case in manifest["cases"]:
        schema_path = CONTRACTS / case["schema"]
        schema = load_json(schema_path)
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())

        for relative_path in case["valid"]:
            validator.validate(load_json(CONTRACTS / relative_path))
            checked += 1

        for relative_path in case["invalid"]:
            errors = list(validator.iter_errors(load_json(CONTRACTS / relative_path)))
            if not errors:
                raise AssertionError(f"expected invalid contract fixture: {relative_path}")
            checked += 1

    print(f"PASS: {len(manifest['cases'])} schemas and {checked} contract fixtures")


if __name__ == "__main__":
    main()
