"""Deterministic smoke gate for DuckDB analytical mart rebuild semantics."""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from routemind_compute.application.analytics_archive import AnalyticalArchive, AnalyticalRecord
from routemind_compute.application.analytics_marts import AnalyticalMartBuilder


def _append(root: Path, record_id: str, dataset: str, payload: dict[str, str]) -> None:
    event_time = datetime(2026, 8, 23, 12, int(record_id[-1]), tzinfo=UTC)
    AnalyticalArchive(root).append(
        AnalyticalRecord(
            record_id=record_id,
            dataset=dataset,
            schema_version="v1",
            event_time=event_time,
            ingestion_time=event_time,
            clock_domain="WALL",
            source_revision="analytics-mart-gate",
            reference_data_id="travel:v1",
            decision_id=record_id if dataset == "dispatch_decisions" else None,
            payload=payload,
        )
    )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="routemind-mart-gate-") as directory:
        root = Path(directory)
        _append(root, "gate-1", "dispatch_decisions", {"strategy": "nearest"})
        _append(root, "gate-2", "orders", {"status": "CREATED"})
        builder = AnalyticalMartBuilder(root)
        first = builder.build("full")
        second = builder.build("full")
        unchanged = builder.build("incremental")
        if first.content_digest != second.content_digest:
            raise SystemExit("mart full rebuild content digest changed")
        if unchanged.inserted_record_count != 0 or unchanged.mart_record_count != 2:
            raise SystemExit(f"mart incremental idempotency failed: {unchanged}")
        print(
            json.dumps(
                {
                    "content_digest": second.content_digest,
                    "full_rebuild_stable": True,
                    "incremental_inserted": unchanged.inserted_record_count,
                    "mart_record_count": unchanged.mart_record_count,
                    "source_digest": second.source_digest,
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
