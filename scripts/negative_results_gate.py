from __future__ import annotations

import hashlib
import json
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    ROOT
    / "docs/research/r3/manifests/negative-results/r3-358-negative-results-audit-v1.json"
)
_SCHEMA = "routemind-negative-results-audit-v1"
_ENTRY_START = re.compile(r"^- `(?P<entry_id>NR-R3-\d{3})`:")


class NegativeResultsGateError(ValueError):
    """Raised when the frozen negative-results audit no longer validates."""


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, allow_nan=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def extract_entries(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    starts = [index for index, line in enumerate(lines) if _ENTRY_START.match(line)]
    entries: list[tuple[str, str]] = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        match = _ENTRY_START.match(lines[start])
        if match is None:  # pragma: no cover - starts is derived from this expression
            raise NegativeResultsGateError("negative-result entry parser drift")
        normalized = "\n".join(line.rstrip() for line in lines[start:end]).rstrip()
        entries.append((match.group("entry_id"), normalized))
    return entries


def prefix_digest(entries: Sequence[tuple[str, str]], count: int) -> str:
    return _canonical_digest(
        [{"entry_id": entry_id, "text": text} for entry_id, text in entries[:count]]
    )


def _load_manifest(path: Path) -> Mapping[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise NegativeResultsGateError(f"cannot read audit manifest: {exc}") from exc
    if not isinstance(value, dict):
        raise NegativeResultsGateError("audit manifest must be an object")
    claimed = value.get("manifest_digest")
    unsigned = dict(value)
    unsigned.pop("manifest_digest", None)
    if not isinstance(claimed, str) or claimed != _canonical_digest(unsigned):
        raise NegativeResultsGateError("audit manifest digest mismatch")
    if value.get("schema_version") != _SCHEMA or value.get("task_id") != "R3-358":
        raise NegativeResultsGateError("audit manifest identity mismatch")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise NegativeResultsGateError(f"{label} must be non-empty text")
    return value


def _array(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise NegativeResultsGateError(f"{label} must be an array")
    return value


def _resolve_below(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    if candidate != root and root not in candidate.parents:
        raise NegativeResultsGateError(f"path escapes repository root: {relative}")
    return candidate


def validate_negative_results(
    root: Path = ROOT, manifest_path: Path | None = None
) -> dict[str, object]:
    repository = root.resolve()
    manifest = _load_manifest((manifest_path or MANIFEST_PATH).resolve())
    ledger = _resolve_below(repository, _text(manifest.get("ledger_path"), "ledger_path"))
    try:
        entries = extract_entries(ledger.read_text(encoding="utf-8"))
    except OSError as exc:
        raise NegativeResultsGateError(f"cannot read negative-result ledger: {exc}") from exc
    count = manifest.get("frozen_entry_count")
    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        raise NegativeResultsGateError("frozen_entry_count must be positive")
    if len(entries) < count:
        raise NegativeResultsGateError("frozen negative-result entries were deleted")
    expected_ids = [f"NR-R3-{index:03d}" for index in range(1, len(entries) + 1)]
    observed_ids = [entry_id for entry_id, _ in entries]
    if observed_ids != expected_ids:
        raise NegativeResultsGateError("negative-result identifiers are not unique and monotonic")
    observed_prefix = prefix_digest(entries, count)
    if observed_prefix != manifest.get("ledger_prefix_digest"):
        raise NegativeResultsGateError("frozen negative-result prefix was modified or reordered")

    frozen_text = "\n".join(text for _, text in entries[:count])
    required_tasks = [
        _text(item, "required task")
        for item in _array(manifest.get("required_task_coverage"), "required_task_coverage")
    ]
    missing_tasks = [task_id for task_id in required_tasks if task_id not in frozen_text]
    if missing_tasks:
        raise NegativeResultsGateError(f"required task coverage is missing: {missing_tasks}")

    categories = manifest.get("category_entries")
    if not isinstance(categories, dict) or not categories:
        raise NegativeResultsGateError("category_entries must be a non-empty object")
    frozen_ids = set(observed_ids[:count])
    for category, category_ids in categories.items():
        if not isinstance(category, str) or not category:
            raise NegativeResultsGateError("category name must be non-empty text")
        references = {_text(item, f"{category} entry") for item in _array(category_ids, category)}
        if not references or not references <= frozen_ids:
            raise NegativeResultsGateError(f"category {category} has invalid entry references")

    source_count = 0
    for item in _array(manifest.get("source_artifacts"), "source_artifacts"):
        if not isinstance(item, dict):
            raise NegativeResultsGateError("source artifact must be an object")
        source = _resolve_below(repository, _text(item.get("path"), "source path"))
        expected_sha = _text(item.get("sha256"), "source sha256")
        try:
            observed_sha = hashlib.sha256(source.read_bytes()).hexdigest()
        except OSError as exc:
            raise NegativeResultsGateError(f"cannot read source artifact {source}: {exc}") from exc
        if observed_sha != expected_sha:
            raise NegativeResultsGateError(f"source artifact digest mismatch: {source}")
        source_count += 1

    return {
        "valid": True,
        "frozen_entry_count": count,
        "total_entry_count": len(entries),
        "ledger_prefix_digest": observed_prefix,
        "required_task_count": len(required_tasks),
        "category_count": len(categories),
        "source_artifact_count": source_count,
    }


def main() -> int:
    try:
        result = validate_negative_results()
    except NegativeResultsGateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
