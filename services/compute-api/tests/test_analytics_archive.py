from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from routemind_compute.application.analytics_archive import (
    AnalyticalArchive,
    AnalyticalRecord,
    ArchiveError,
    ArchiveIntegrityError,
    ArchiveRootNotConfiguredError,
    DuplicateArchiveRecordError,
)


def _record(record_id: str = "evt-1", *, day: int = 23) -> AnalyticalRecord:
    event_time = datetime(2026, 8, day, 12, 0, tzinfo=UTC)
    return AnalyticalRecord(
        record_id=record_id,
        dataset="dispatch_decisions",
        schema_version="v1",
        event_time=event_time,
        ingestion_time=event_time.replace(minute=1),
        clock_domain="WALL",
        source_revision="test-revision",
        trace_id="trace-1",
        correlation_id="corr-1",
        reference_data_id="travel:v1",
        decision_id="decision-1",
        payload={"strategy": "nearest", "selected": "courier-1"},
    )


def test_archive_requires_external_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ROUTEMIND_DATA_ROOT", raising=False)
    with pytest.raises(ArchiveRootNotConfiguredError):
        AnalyticalArchive()


def test_append_partitions_and_records_provenance(tmp_path: Path) -> None:
    archive = AnalyticalArchive(tmp_path)
    result = archive.append(_record())

    assert result.path == tmp_path / "dispatch_decisions" / "date=2026-08-23" / "events.jsonl"
    assert result.duplicate is False
    payload = json.loads(result.path.read_text(encoding="utf-8"))
    assert payload["clock_domain"] == "WALL"
    assert payload["reference_data_id"] == "travel:v1"
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["archive_format"] == "jsonl"
    assert manifest["partitions"][0]["record_count"] == 1
    assert manifest["partitions"][0]["sha256"] == result.manifest_digest


def test_duplicate_record_ids_are_rejected_across_partitions(tmp_path: Path) -> None:
    archive = AnalyticalArchive(tmp_path)
    archive.append(_record(day=23))
    with pytest.raises(DuplicateArchiveRecordError):
        archive.append(_record(day=24))


def test_rebuild_and_verify_report_unique_records(tmp_path: Path) -> None:
    archive = AnalyticalArchive(tmp_path)
    archive.append(_record("evt-1", day=23))
    archive.append(_record("evt-2", day=24))

    manifest = archive.rebuild_manifest()
    report = archive.verify()
    assert len(manifest["partitions"]) == 2
    assert report == {
        "manifest_version": "v1",
        "partition_count": 2,
        "record_count": 2,
        "unique_record_ids": 2,
        "valid": True,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("dataset", "../secrets"),
        ("clock_domain", "UNKNOWN"),
        ("event_time", datetime(2026, 8, 23, 12, 0)),
    ],
)
def test_record_contract_rejects_unsafe_values(field: str, value: object, tmp_path: Path) -> None:
    record = _record()
    values = {**record.__dict__, field: value}
    with pytest.raises(ArchiveError):
        AnalyticalArchive(tmp_path).append(AnalyticalRecord(**values))


def test_verify_rejects_corrupt_existing_line(tmp_path: Path) -> None:
    archive = AnalyticalArchive(tmp_path)
    archive.append(_record())
    data_path = tmp_path / "dispatch_decisions" / "date=2026-08-23" / "events.jsonl"
    data_path.write_text(data_path.read_text(encoding="utf-8") + "{broken\n", encoding="utf-8")
    with pytest.raises(ArchiveIntegrityError):
        archive.verify()
