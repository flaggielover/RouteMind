"""Executable semantic metric contract and denominator gate."""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from routemind_compute.application.analytics_archive import AnalyticalArchive, AnalyticalRecord
from routemind_compute.application.analytics_marts import AnalyticalMartBuilder
from routemind_compute.application.semantic_metrics import SemanticMetricEngine, metric_catalog


def _append(root: Path, record_id: str, selected: str, fallback: bool) -> None:
    instant = datetime(2026, 8, 23, 12, int(record_id[-1]), tzinfo=UTC)
    AnalyticalArchive(root).append(
        AnalyticalRecord(
            record_id=record_id,
            dataset="dispatch_decisions",
            schema_version="v1",
            event_time=instant,
            ingestion_time=instant,
            clock_domain="WALL",
            source_revision="semantic-metric-gate",
            decision_id=record_id,
            payload={"selected_courier": selected, "fallback_used": fallback},
        )
    )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="routemind-metric-gate-") as directory:
        root = Path(directory)
        _append(root, "gate-1", "courier-1", False)
        _append(root, "gate-2", "", True)
        database = AnalyticalMartBuilder(root).build("full").database_path
        start = datetime(2026, 8, 23, 12, tzinfo=UTC)
        results = SemanticMetricEngine(database).evaluate(
            ("dispatch_assignment_rate", "dispatch_fallback_rate"),
            start,
            start + timedelta(hours=1),
        )
        if [result.value for result in results] != [0.5, 0.5]:
            raise SystemExit(f"semantic metric results changed: {results}")
        catalogs = {
            consumer: [item.definition_digest for item in metric_catalog(consumer)]
            for consumer in ("web", "report", "agent")
        }
        if catalogs["web"] != catalogs["report"] or catalogs["web"] != catalogs["agent"]:
            raise SystemExit("semantic metric consumers received different definitions")
        print(
            json.dumps(
                {
                    "consumer_catalog_consistent": True,
                    "metric_count": len(catalogs["web"]),
                    "results": {result.name: result.value for result in results},
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
