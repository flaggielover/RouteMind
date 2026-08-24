"""CLI for generating a read-only report from retained R3-325 artifacts."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence
from pathlib import Path

from routemind_compute.application.statistical_routebench_report import (
    build_statistical_routebench_report,
    write_statistical_routebench_report,
)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    campaign_directory = (
        arguments.data_root.resolve() / "experiments" / "r3" / "R3-325" / arguments.campaign_id
    )
    report = build_statistical_routebench_report(campaign_directory, arguments.protocol)
    output_path = write_statistical_routebench_report(report, campaign_directory)
    print(
        json.dumps(
            {
                "campaign_id": report.campaign_id,
                "report_digest": report.report_digest,
                "report_path": str(output_path),
                "cell_count": len(report.cells),
                "multiplicity_disposition": report.multiplicity["disposition"],
                "claim_boundary": report.claim_boundary,
            },
            sort_keys=True,
        )
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a read-only report from a retained Statistical RouteBench pilot"
    )
    configured_root = os.getenv("ROUTEMIND_DATA_ROOT")
    parser.add_argument(
        "--data-root",
        type=Path,
        required=configured_root is None,
        default=Path(configured_root) if configured_root else None,
    )
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path(
            "docs/research/r3/manifests/statistical-routebench/statistical-routebench-v1.json"
        ),
    )
    return parser


__all__ = ["main"]
