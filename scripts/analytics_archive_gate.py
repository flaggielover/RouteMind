"""Deterministic smoke gate for the external analytical archive contract."""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from routemind_compute.application.analytics_archive import (
    AnalyticalArchive,
    AnalyticalRecord,
    DuplicateArchiveRecordError,
)


def _record(record_id: str) -> AnalyticalRecord:
    event_time = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)
    return AnalyticalRecord(
        record_id=record_id,
        dataset="dispatch_decisions",
        schema_version="v1",
        event_time=event_time,
        ingestion_time=event_time.replace(minute=1),
        clock_domain="WALL",
        source_revision="analytics-archive-gate",
        trace_id="trace-gate",
        correlation_id="correlation-gate",
        reference_data_id="travel:v1",
        decision_id=f"decision-{record_id}",
        payload={"strategy": "nearest", "selected": "courier-1"},
    )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="routemind-archive-gate-") as directory:
        archive = AnalyticalArchive(Path(directory))
        archive.append(_record("gate-1"))
        archive.append(_record("gate-2"))
        duplicate_rejected = False
        try:
            archive.append(_record("gate-1"))
        except DuplicateArchiveRecordError:
            duplicate_rejected = True
        report = archive.verify()
        if not duplicate_rejected or not report["valid"] or report["record_count"] != 2:
            raise SystemExit(f"archive gate failed: {report}")
        print(json.dumps({"duplicate_rejected": True, **report}, sort_keys=True))


if __name__ == "__main__":
    main()
