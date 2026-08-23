"""Reproducible DuckDB marts over the external analytical archive."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import duckdb

from routemind_compute.application.analytics_archive import ArchiveIntegrityError

BuildMode = Literal["full", "incremental"]
_MANIFEST = "manifest.json"
_DATABASE = "marts/routemind.duckdb"


@dataclass(frozen=True)
class MartBuildResult:
    database_path: Path
    mode: BuildMode
    source_partition_count: int
    source_record_count: int
    inserted_record_count: int
    mart_record_count: int
    source_digest: str
    content_digest: str


class AnalyticalMartBuilder:
    """Build deterministic read models without owning business state."""

    def __init__(self, archive_root: Path | str) -> None:
        self.archive_root = Path(archive_root).expanduser().resolve()
        self.database_path = self.archive_root / _DATABASE

    def build(self, mode: BuildMode = "full") -> MartBuildResult:
        if mode not in {"full", "incremental"}:
            raise ValueError(f"unsupported mart build mode: {mode}")
        manifest = self._load_manifest()
        source_digest = _manifest_source_digest(manifest)
        target = self.database_path
        target.parent.mkdir(parents=True, exist_ok=True)
        working = target.with_suffix(".duckdb.tmp") if mode == "full" else target
        if mode == "full" and working.exists():
            working.unlink()

        connection = duckdb.connect(str(working))
        inserted = 0
        source_records = 0
        try:
            _create_schema(connection)
            for partition in manifest["partitions"]:
                data_path = self.archive_root / str(partition["path"])
                _verify_partition(data_path, partition)
                for line_number, line in enumerate(
                    data_path.read_text(encoding="utf-8").splitlines(), start=1
                ):
                    source_records += 1
                    record = _parse_record(data_path, line_number, line)
                    inserted += _insert_record(connection, record)
            _refresh_dimensions(connection)
            content_digest = _content_digest(connection)
            mart_records = int(_scalar(connection, "SELECT count(*) FROM fact_event"))
            connection.commit()
        finally:
            connection.close()

        if mode == "full":
            os.replace(working, target)
        return MartBuildResult(
            database_path=target,
            mode=mode,
            source_partition_count=len(manifest["partitions"]),
            source_record_count=source_records,
            inserted_record_count=inserted,
            mart_record_count=mart_records,
            source_digest=source_digest,
            content_digest=content_digest,
        )

    def _load_manifest(self) -> dict[str, Any]:
        path = self.archive_root / _MANIFEST
        if not path.is_file():
            raise ArchiveIntegrityError(f"analytical archive manifest missing: {path}")
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ArchiveIntegrityError(f"invalid analytical manifest: {path}") from exc
        if not isinstance(manifest, dict) or manifest.get("manifest_version") != "v1":
            raise ArchiveIntegrityError("unsupported analytical manifest")
        partitions = manifest.get("partitions")
        if not isinstance(partitions, list):
            raise ArchiveIntegrityError("analytical manifest partitions missing")
        return manifest


def _create_schema(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS fact_event (
            record_id VARCHAR PRIMARY KEY,
            dataset VARCHAR NOT NULL,
            schema_version VARCHAR NOT NULL,
            event_time TIMESTAMPTZ NOT NULL,
            ingestion_time TIMESTAMPTZ NOT NULL,
            clock_domain VARCHAR NOT NULL,
            source_revision VARCHAR NOT NULL,
            trace_id VARCHAR,
            correlation_id VARCHAR,
            reference_data_id VARCHAR,
            decision_id VARCHAR,
            payload_json JSON NOT NULL
        );
        CREATE TABLE IF NOT EXISTS dim_strategy (
            strategy_name VARCHAR PRIMARY KEY,
            first_event_time TIMESTAMPTZ NOT NULL,
            last_event_time TIMESTAMPTZ NOT NULL,
            decision_count BIGINT NOT NULL
        );
        CREATE OR REPLACE VIEW fact_decision AS
            SELECT * FROM fact_event WHERE dataset = 'dispatch_decisions';
        CREATE OR REPLACE VIEW fact_order AS
            SELECT * FROM fact_event WHERE dataset = 'orders';
        CREATE OR REPLACE VIEW fact_order_transition AS
            SELECT * FROM fact_event WHERE dataset = 'order_transitions';
        CREATE OR REPLACE VIEW fact_location_observation AS
            SELECT * FROM fact_event WHERE dataset = 'courier_locations';
        CREATE OR REPLACE VIEW fact_solver_run AS
            SELECT * FROM fact_event WHERE dataset = 'solver_runs';
        CREATE OR REPLACE VIEW fact_simulation_run AS
            SELECT * FROM fact_event WHERE dataset = 'simulation_runs';
        """
    )


def _verify_partition(path: Path, partition: dict[str, Any]) -> None:
    if not path.is_file():
        raise ArchiveIntegrityError(f"archive partition missing: {path}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != partition.get("sha256"):
        raise ArchiveIntegrityError(f"archive partition digest mismatch: {path}")


def _parse_record(path: Path, line_number: int, line: str) -> dict[str, Any]:
    try:
        parsed = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ArchiveIntegrityError(f"invalid JSON at {path}:{line_number}") from exc
    required = {
        "record_id",
        "dataset",
        "schema_version",
        "event_time",
        "ingestion_time",
        "clock_domain",
        "source_revision",
        "payload",
    }
    if not isinstance(parsed, dict) or not required.issubset(parsed):
        raise ArchiveIntegrityError(f"invalid analytical record at {path}:{line_number}")
    return parsed


def _insert_record(connection: duckdb.DuckDBPyConnection, record: dict[str, Any]) -> int:
    before = int(_scalar(connection, "SELECT count(*) FROM fact_event"))
    connection.execute(
        """
        INSERT INTO fact_event VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (record_id) DO NOTHING
        """,
        [
            record["record_id"],
            record["dataset"],
            record["schema_version"],
            record["event_time"],
            record["ingestion_time"],
            record["clock_domain"],
            record["source_revision"],
            record.get("trace_id"),
            record.get("correlation_id"),
            record.get("reference_data_id"),
            record.get("decision_id"),
            json.dumps(record["payload"], sort_keys=True, separators=(",", ":")),
        ],
    )
    after = int(_scalar(connection, "SELECT count(*) FROM fact_event"))
    return after - before


def _refresh_dimensions(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute("DELETE FROM dim_strategy")
    connection.execute(
        """
        INSERT INTO dim_strategy
        SELECT
            json_extract_string(payload_json, '$.strategy') AS strategy_name,
            min(event_time),
            max(event_time),
            count(*)
        FROM fact_decision
        WHERE json_extract_string(payload_json, '$.strategy') IS NOT NULL
        GROUP BY strategy_name
        """
    )


def _manifest_source_digest(manifest: dict[str, Any]) -> str:
    source = [
        (str(item["path"]), str(item["sha256"]), int(item["record_count"]))
        for item in manifest["partitions"]
    ]
    encoded = json.dumps(source, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _content_digest(connection: duckdb.DuckDBPyConnection) -> str:
    rows = connection.execute(
        """
        SELECT record_id, dataset, schema_version,
               strftime(event_time AT TIME ZONE 'UTC', '%Y-%m-%dT%H:%M:%S.%gZ'),
               strftime(ingestion_time AT TIME ZONE 'UTC', '%Y-%m-%dT%H:%M:%S.%gZ'),
               clock_domain, source_revision, coalesce(trace_id, ''),
               coalesce(correlation_id, ''), coalesce(reference_data_id, ''),
               coalesce(decision_id, ''), payload_json::VARCHAR
        FROM fact_event
        ORDER BY record_id
        """
    ).fetchall()
    encoded = json.dumps(rows, default=str, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _scalar(connection: duckdb.DuckDBPyConnection, query: str) -> Any:
    row = connection.execute(query).fetchone()
    if row is None:
        raise ArchiveIntegrityError(f"mart scalar query returned no row: {query}")
    return row[0]


__all__ = ["AnalyticalMartBuilder", "MartBuildResult"]
