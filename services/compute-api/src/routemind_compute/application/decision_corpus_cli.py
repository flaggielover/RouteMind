"""Build a privacy-bounded Decision Corpus from an explicit JSON source."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from routemind_compute.application.decision_corpus import (
    build_decision_corpus,
    write_decision_corpus,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--data-root", type=Path)
    args = parser.parse_args(argv)
    root = args.data_root or _environment_root()
    source = _read_source(args.input)
    corpus = build_decision_corpus(
        _records(source),
        corpus_id=_text(source, "corpus_id"),
        source_manifest_id=_text(source, "source_manifest_id"),
        source_manifest_digest=_text(source, "source_manifest_digest"),
        code_revision=_text(source, "code_revision"),
    )
    path = write_decision_corpus(corpus, root)
    print(
        json.dumps(
            {
                "corpus_id": corpus.corpus_id,
                "record_count": len(corpus.records),
                "manifest_digest": corpus.manifest_digest,
                "manifest_path": str(path),
                "retention_boundary": "no_raw_trajectories_or_direct_identifiers",
            },
            sort_keys=True,
        )
    )
    return 0


def _environment_root() -> Path:
    configured = os.environ.get("ROUTEMIND_DATA_ROOT", "").strip()
    if not configured:
        raise ValueError("--data-root or ROUTEMIND_DATA_ROOT is required")
    return Path(configured)


def _read_source(path: Path) -> Mapping[str, object]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, Mapping):
        raise ValueError("input source must be a JSON object")
    return parsed


def _records(source: Mapping[str, object]) -> Sequence[Mapping[str, object]]:
    value = source.get("records")
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError("input source records must be an array")
    if not all(isinstance(item, Mapping) for item in value):
        raise ValueError("input source records must be objects")
    return cast(Sequence[Mapping[str, object]], value)


def _text(source: Mapping[str, object], key: str) -> str:
    value = source.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"input source {key} must be non-empty text")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
