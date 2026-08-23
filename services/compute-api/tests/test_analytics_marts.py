from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pytest

from routemind_compute.application.analytics_archive import (
    AnalyticalArchive,
    AnalyticalRecord,
    ArchiveIntegrityError,
)
from routemind_compute.application.analytics_marts import AnalyticalMartBuilder


def _append(root: Path, record_id: str, dataset: str, payload: dict[str, str]) -> None:
    timestamp = datetime(2026, 8, 23, 12, int(record_id[-1]), tzinfo=UTC)
    AnalyticalArchive(root).append(
        AnalyticalRecord(
            record_id=record_id,
            dataset=dataset,
            schema_version="v1",
            event_time=timestamp,
            ingestion_time=timestamp,
            clock_domain="WALL",
            source_revision="test-revision",
            trace_id=f"trace-{record_id}",
            reference_data_id="travel:v1",
            decision_id=record_id if dataset == "dispatch_decisions" else None,
            payload=payload,
        )
    )


def test_full_build_creates_curated_views_and_strategy_dimension(tmp_path: Path) -> None:
    _append(tmp_path, "evt-1", "dispatch_decisions", {"strategy": "nearest"})
    _append(tmp_path, "evt-2", "orders", {"status": "CREATED"})

    result = AnalyticalMartBuilder(tmp_path).build("full")

    assert result.source_record_count == 2
    assert result.inserted_record_count == 2
    assert result.mart_record_count == 2
    assert len(result.source_digest) == 64
    assert len(result.content_digest) == 64
    with duckdb.connect(str(result.database_path), read_only=True) as connection:
        decision_count = connection.execute("SELECT count(*) FROM fact_decision").fetchone()
        order_count = connection.execute("SELECT count(*) FROM fact_order").fetchone()
        strategy = connection.execute("SELECT strategy_name FROM dim_strategy").fetchone()
        assert decision_count == (1,)
        assert order_count == (1,)
        assert strategy == ("nearest",)


def test_full_rebuild_has_stable_content_digest(tmp_path: Path) -> None:
    _append(tmp_path, "evt-1", "dispatch_decisions", {"strategy": "nearest"})
    builder = AnalyticalMartBuilder(tmp_path)
    first = builder.build("full")
    second = builder.build("full")
    assert first.content_digest == second.content_digest
    assert first.source_digest == second.source_digest


def test_incremental_build_is_idempotent_and_adds_new_records(tmp_path: Path) -> None:
    _append(tmp_path, "evt-1", "orders", {"status": "CREATED"})
    builder = AnalyticalMartBuilder(tmp_path)
    builder.build("full")
    unchanged = builder.build("incremental")
    assert unchanged.inserted_record_count == 0

    _append(tmp_path, "evt-2", "order_transitions", {"status": "ACCEPTED"})
    updated = builder.build("incremental")
    assert updated.inserted_record_count == 1
    assert updated.mart_record_count == 2


def test_digest_mismatch_fails_before_loading(tmp_path: Path) -> None:
    _append(tmp_path, "evt-1", "orders", {"status": "CREATED"})
    data_path = tmp_path / "orders" / "date=2026-08-23" / "events.jsonl"
    data_path.write_text(data_path.read_text(encoding="utf-8") + "{}\n", encoding="utf-8")
    with pytest.raises(ArchiveIntegrityError, match="digest mismatch"):
        AnalyticalMartBuilder(tmp_path).build("full")


def test_missing_manifest_fails_explicitly(tmp_path: Path) -> None:
    with pytest.raises(ArchiveIntegrityError, match="manifest missing"):
        AnalyticalMartBuilder(tmp_path).build("full")


def test_unknown_mode_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsupported mart build mode"):
        AnalyticalMartBuilder(tmp_path).build("replace")  # type: ignore[arg-type]
