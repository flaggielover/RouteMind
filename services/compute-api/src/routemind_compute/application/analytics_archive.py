"""Append-only analytical archive with explicit provenance and rebuildable manifests."""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SAFE_NAME = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
_DATA_FILE = "events.jsonl"
_MANIFEST_FILE = "manifest.json"


class ArchiveError(ValueError):
    """Base error for archive contract violations."""


class ArchiveRootNotConfiguredError(ArchiveError):
    """Raised when no archive root is available."""


class DuplicateArchiveRecordError(ArchiveError):
    """Raised when a record ID has already been archived."""


class ArchiveIntegrityError(ArchiveError):
    """Raised when an existing archive line or manifest is malformed."""


@dataclass(frozen=True)
class AnalyticalRecord:
    """One immutable analytical event or decision observation."""

    record_id: str
    dataset: str
    schema_version: str
    event_time: datetime
    ingestion_time: datetime
    clock_domain: str
    source_revision: str
    payload: Mapping[str, Any]
    trace_id: str | None = None
    correlation_id: str | None = None
    reference_data_id: str | None = None
    decision_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        _validate_record(self)
        return {
            "record_id": self.record_id,
            "dataset": self.dataset,
            "schema_version": self.schema_version,
            "event_time": _format_time(self.event_time),
            "ingestion_time": _format_time(self.ingestion_time),
            "clock_domain": self.clock_domain,
            "source_revision": self.source_revision,
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "reference_data_id": self.reference_data_id,
            "decision_id": self.decision_id,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class ArchiveAppendResult:
    path: Path
    record_id: str
    duplicate: bool
    manifest_digest: str


class AnalyticalArchive:
    """Append records under a configured external data root.

    The JSONL files are the append-only source. Manifests are derived metadata
    and can be rebuilt after a partial write or interrupted manifest update.
    """

    def __init__(self, root: Path | str | None = None) -> None:
        configured = root if root is not None else os.getenv("ROUTEMIND_DATA_ROOT")
        if not configured:
            raise ArchiveRootNotConfiguredError(
                "ROUTEMIND_DATA_ROOT must be configured for analytical archives"
            )
        self.root = Path(configured).expanduser().resolve()
        self._lock = threading.RLock()

    def append(self, record: AnalyticalRecord) -> ArchiveAppendResult:
        """Append one validated record and refresh its derived manifest."""

        payload = record.as_dict()
        with self._lock:
            if self._record_exists(record.record_id):
                raise DuplicateArchiveRecordError(
                    f"archive record already exists: {record.record_id}"
                )
            partition_date = record.event_time.astimezone(UTC).date().isoformat()
            partition = self.root / record.dataset / f"date={partition_date}"
            partition.mkdir(parents=True, exist_ok=True)
            data_path = partition / _DATA_FILE
            encoded = _canonical_json(payload) + "\n"
            with data_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded)
            manifest = self.rebuild_manifest()
            partition_manifest = next(
                item
                for item in manifest["partitions"]
                if item["path"] == _relative_path(self.root, data_path)
            )
            return ArchiveAppendResult(
                path=data_path,
                record_id=record.record_id,
                duplicate=False,
                manifest_digest=partition_manifest["sha256"],
            )

    def rebuild_manifest(self) -> dict[str, Any]:
        """Scan source JSONL files and atomically write a derived manifest."""

        with self._lock:
            partitions: list[dict[str, Any]] = []
            if self.root.exists():
                for data_path in sorted(self.root.rglob(_DATA_FILE)):
                    partitions.append(self._partition_manifest(data_path))
            manifest = {
                "manifest_version": "v1",
                "archive_format": "jsonl",
                "root_policy": "ROUTEMIND_DATA_ROOT",
                "partitions": partitions,
            }
            self.root.mkdir(parents=True, exist_ok=True)
            _atomic_write(self.root / _MANIFEST_FILE, manifest)
            return manifest

    def verify(self) -> dict[str, Any]:
        """Validate all source lines and compare the derived manifest."""

        manifest = self.rebuild_manifest()
        record_ids: set[str] = set()
        record_count = 0
        for data_path in sorted(self.root.rglob(_DATA_FILE)):
            for line_number, line in enumerate(
                data_path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ArchiveIntegrityError(
                        f"invalid JSON at {data_path}:{line_number}"
                    ) from exc
                if not isinstance(parsed, dict) or not parsed.get("record_id"):
                    raise ArchiveIntegrityError(f"record_id missing at {data_path}:{line_number}")
                record_id = str(parsed["record_id"])
                if record_id in record_ids:
                    raise ArchiveIntegrityError(f"duplicate record_id: {record_id}")
                record_ids.add(record_id)
                record_count += 1
        return {
            "manifest_version": manifest["manifest_version"],
            "partition_count": len(manifest["partitions"]),
            "record_count": record_count,
            "unique_record_ids": len(record_ids),
            "valid": record_count == len(record_ids),
        }

    def _record_exists(self, record_id: str) -> bool:
        for data_path in self.root.rglob(_DATA_FILE) if self.root.exists() else ():
            for line in data_path.read_text(encoding="utf-8").splitlines():
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ArchiveIntegrityError(f"invalid JSON in {data_path}") from exc
                if isinstance(parsed, dict) and parsed.get("record_id") == record_id:
                    return True
        return False

    def _partition_manifest(self, data_path: Path) -> dict[str, Any]:
        raw = data_path.read_bytes()
        records: list[dict[str, Any]] = []
        for line_number, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ArchiveIntegrityError(f"invalid JSON at {data_path}:{line_number}") from exc
            if not isinstance(parsed, dict) or not parsed.get("record_id"):
                raise ArchiveIntegrityError(f"record_id missing at {data_path}:{line_number}")
            records.append(parsed)
        event_times = sorted(str(item["event_time"]) for item in records)
        return {
            "path": _relative_path(self.root, data_path),
            "dataset": data_path.parent.parent.name,
            "partition": data_path.parent.name,
            "record_count": len(records),
            "schema_versions": sorted({str(item["schema_version"]) for item in records}),
            "source_revisions": sorted({str(item["source_revision"]) for item in records}),
            "first_event_time": event_times[0] if event_times else None,
            "last_event_time": event_times[-1] if event_times else None,
            "byte_size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }


def _validate_record(record: AnalyticalRecord) -> None:
    for field_name in ("record_id", "schema_version", "source_revision"):
        value = getattr(record, field_name)
        if not isinstance(value, str) or not value.strip():
            raise ArchiveError(f"{field_name} is required")
    if not _SAFE_NAME.fullmatch(record.dataset):
        raise ArchiveError(f"invalid dataset name: {record.dataset!r}")
    if record.clock_domain not in {"WALL", "SIMULATED", "REPLAY"}:
        raise ArchiveError(f"unsupported clock domain: {record.clock_domain!r}")
    for field_name in ("event_time", "ingestion_time"):
        value = getattr(record, field_name)
        if value.tzinfo is None or value.utcoffset() is None:
            raise ArchiveError(f"{field_name} must be timezone-aware")
    if not isinstance(record.payload, Mapping):
        raise ArchiveError("payload must be a mapping")
    try:
        json.dumps(record.payload, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise ArchiveError("payload must be JSON serializable") from exc


def _format_time(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _relative_path(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(_canonical_json(value) + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, path)


__all__ = [
    "AnalyticalArchive",
    "AnalyticalRecord",
    "ArchiveAppendResult",
    "ArchiveError",
    "ArchiveIntegrityError",
    "ArchiveRootNotConfiguredError",
    "DuplicateArchiveRecordError",
]
