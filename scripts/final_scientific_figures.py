from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = (
    ROOT
    / "docs"
    / "research"
    / "r3"
    / "manifests"
    / "final-figures"
    / "r3-360-final-figures-v2.json"
)
EXPECTED_REGIMES = [
    "normal",
    "surge",
    "shortage",
    "merchant-delay",
    "travel-degradation",
    "location-staleness",
    "compute-budget",
    "queue-pressure",
]
EXPECTED_CLAIMS = ["R3-A1", "R3-A2", "R3-B1", "R3-C1", "R3-D1", "R3-D2", "R3-E1"]
SVG_NS = "http://www.w3.org/2000/svg"


class FinalFiguresError(ValueError):
    pass


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FinalFiguresError(f"cannot load JSON: {path}") from exc
    if not isinstance(value, dict):
        raise FinalFiguresError(f"JSON root must be an object: {path}")
    return value


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError as exc:
        raise FinalFiguresError(f"cannot read artifact: {path}") from exc


def _canonical_digest(value: dict[str, Any], omitted_key: str) -> str:
    content = {key: item for key, item in value.items() if key != omitted_key}
    encoded = json.dumps(
        content, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return _sha256_bytes(encoded)


def validate_plan(plan: dict[str, Any]) -> None:
    if plan.get("schema_version") != "routemind-final-scientific-figures-plan-v1":
        raise FinalFiguresError("figure plan schema drifted")
    if plan.get("task_id") != "R3-360" or plan.get("plan_id") != (
        "r3-360-final-scientific-figures-v2"
    ):
        raise FinalFiguresError("figure plan identity drifted")
    if plan.get("plan_digest") != _canonical_digest(plan, "plan_digest"):
        raise FinalFiguresError("figure plan digest mismatch")
    policy = plan.get("execution_policy", {})
    if policy != {
        "run_experiments": False,
        "rerun_r3_325": False,
        "tune_or_reinterpret": False,
        "synthetic_fill": False,
        "drop_negative_outcomes": False,
    }:
        raise FinalFiguresError("figure execution policy drifted")
    if len(plan.get("figures", [])) != 3 or len(plan.get("tables", [])) != 3:
        raise FinalFiguresError("figure/table inventory drifted")


def _resolve_below(root: Path, relative_path: str) -> Path:
    resolved_root = root.resolve()
    candidate = (resolved_root / relative_path).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise FinalFiguresError("artifact path escaped its declared root") from exc
    return candidate


def _verify_repository_sources(plan: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = {}
    for source_id, source in plan["sources"].items():
        if source["scope"] != "repository":
            continue
        path = _resolve_below(repo_root, source["relative_path"])
        if _sha256_file(path) != source["byte_sha256"]:
            raise FinalFiguresError(f"repository source hash drifted: {source_id}")
        loaded[source_id] = (
            path.read_text(encoding="utf-8") if path.suffix == ".md" else _json(path)
        )
    return loaded


def _verify_external_report(plan: dict[str, Any], data_root: Path) -> dict[str, Any]:
    source = plan["sources"]["routebench_report"]
    path = _resolve_below(data_root, source["relative_path"])
    if _sha256_file(path) != source["byte_sha256"]:
        raise FinalFiguresError("RouteBench report byte hash drifted")
    sidecar = path.with_name(f"{path.name}.sha256")
    try:
        sidecar_hash = sidecar.read_text(encoding="ascii").strip().split()[0]
    except (OSError, IndexError) as exc:
        raise FinalFiguresError("RouteBench report sidecar is missing or invalid") from exc
    if sidecar_hash != source["byte_sha256"]:
        raise FinalFiguresError("RouteBench report sidecar mismatch")
    artifact = _json(path)
    if artifact.get("report_digest") != source["content_digest"]:
        raise FinalFiguresError("RouteBench report digest drifted")
    if artifact.get("report", {}).get("protocol_sha256") != source["protocol_sha256"]:
        raise FinalFiguresError("RouteBench protocol identity drifted")
    return artifact


def extract_routebench_cells(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    report = artifact.get("report", {})
    if report.get("multiplicity", {}).get("disposition") != "CONFIRMATORY_NOT_EXECUTED":
        raise FinalFiguresError("confirmatory disposition drifted")
    source_cells = report.get("cells", [])
    identities = [(cell.get("regime_id"), cell.get("metric_id")) for cell in source_cells]
    expected = [
        (regime, metric)
        for regime in EXPECTED_REGIMES
        for metric in ("scenario_risk_index", "assignment_rate")
    ]
    if identities != expected:
        raise FinalFiguresError("RouteBench cell identities or order drifted")

    rows: list[dict[str, Any]] = []
    for cell in source_cells:
        status = cell.get("status")
        metric_id = cell["metric_id"]
        row: dict[str, Any] = {
            "regime_id": cell["regime_id"],
            "metric_id": metric_id,
            "unit": (
                "unitless paired difference"
                if metric_id == "scenario_risk_index"
                else "proportion paired difference"
            ),
            "n_pairs": cell.get("n"),
            "status": status,
            "mean_difference": None,
            "ci95_lower": None,
            "ci95_upper": None,
            "uncertainty_method": "NOT_ESTIMABLE",
            "exclusion_status": "RETAINED",
            "negative_outcome": cell.get("failure_code") or "NONE",
            "confirmatory_status": "NOT_EXECUTED",
        }
        if row["n_pairs"] != 8:
            raise FinalFiguresError("RouteBench pilot pair count drifted")
        if status == "PLANNED":
            estimate = cell.get("estimate")
            if not isinstance(estimate, dict):
                raise FinalFiguresError("estimable cell lacks estimate")
            interval = estimate.get("interval", {})
            if interval.get("confidence_level") != 0.95:
                raise FinalFiguresError("RouteBench confidence level drifted")
            row.update(
                {
                    "mean_difference": estimate.get("mean_difference"),
                    "ci95_lower": interval.get("lower"),
                    "ci95_upper": interval.get("upper"),
                    "uncertainty_method": interval.get("method"),
                }
            )
            if not all(
                isinstance(row[key], (int, float))
                for key in ("mean_difference", "ci95_lower", "ci95_upper")
            ):
                raise FinalFiguresError("estimable cell has nonnumeric interval")
        elif status == "NON_ESTIMABLE":
            if cell.get("failure_code") != "NON_ESTIMABLE_PAIRED_VARIANCE_OR_POWER":
                raise FinalFiguresError("non-estimable reason drifted")
        else:
            raise FinalFiguresError(f"unexpected RouteBench status: {status}")
        rows.append(row)
    return rows


def _reproduction_observations(reproduction: dict[str, Any], task_id: str) -> dict[str, Any]:
    targets = [target for target in reproduction.get("target_results", []) if target.get("task_id") == task_id]
    if len(targets) != 1 or targets[0].get("status") != "REPRODUCED":
        raise FinalFiguresError(f"missing reproduced target: {task_id}")
    observations = targets[0].get("observations")
    if not isinstance(observations, dict):
        raise FinalFiguresError(f"missing reproduced observations: {task_id}")
    return observations


def build_support_rows(
    twin_manifest: dict[str, Any],
    rads_manifest: dict[str, Any],
    reproduction: dict[str, Any],
) -> list[dict[str, Any]]:
    if twin_manifest.get("plan_digest") != (
        "ed63c2a2c7a8020076411f285ff3c7fccd3b12e7800de70c4ad5b4a9a674dd94"
    ):
        raise FinalFiguresError("Twin plan digest drifted")
    if rads_manifest.get("plan_digest") != (
        "379f5087f3114f50cd9bb8cefff62af0d9a35e0ea3e1ba12544b9fafc52527a2"
    ):
        raise FinalFiguresError("RADS plan digest drifted")
    twin = _reproduction_observations(reproduction, "R3-336")
    rads = _reproduction_observations(reproduction, "R3-349")
    if twin.get("observed_record_count") != 0 or twin.get("status") != "INSUFFICIENT_DATA":
        raise FinalFiguresError("Twin no-data result drifted")
    if rads.get("status") != "INSUFFICIENT_DATA" or rads.get("pairs_per_existing_regime") != 8:
        raise FinalFiguresError("RADS support result drifted")

    rows = [
        {
            "task_id": "R3-336",
            "category": metric,
            "unit": "observed records",
            "observed": 0,
            "required": "held-out observations required",
            "status": "NOT_EVALUATED_NO_DATA",
            "uncertainty": "NOT_COMPUTED_NO_DATA",
            "exclusion_status": "NONE_ZERO_RECORDS_RETAINED",
            "claim_status": "C-NO-CLAIM",
        }
        for metric in twin_manifest["threshold_policy"]["metric_ids"]
    ]
    source_axes = set(rads.get("source_regime_axes", []))
    unsupported_axes = set(rads.get("unsupported_axes", []))
    for axis in [item["axis"] for item in rads_manifest["robustness_axes"]]:
        if axis in source_axes:
            observed = rads["pairs_per_existing_regime"]
            status = "SOURCE_REGIME_PRESENT_NO_RADS_OUTCOME"
        elif axis in unsupported_axes:
            observed = 0
            status = "UNSUPPORTED_REGIME_NOT_PRESENT"
        else:
            raise FinalFiguresError(f"RADS axis support is unaccounted: {axis}")
        rows.append(
            {
                "task_id": "R3-349",
                "category": axis,
                "unit": "paired units per axis level",
                "observed": observed,
                "required": rads["minimum_pairs_per_axis_level"],
                "status": status,
                "uncertainty": "NOT_COMPUTED_NO_RADS_OUTCOMES",
                "exclusion_status": "NONE_UNSUPPORTED_STATE_RETAINED",
                "claim_status": "C-NO-CLAIM",
            }
        )
    if len(rows) != 12:
        raise FinalFiguresError("support table row count drifted")
    return rows


def extract_claim_rows(matrix: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in matrix.splitlines():
        if not line.startswith("| R3-"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 10:
            raise FinalFiguresError("Claim Matrix column count drifted")
        statuses = re.findall(r"\bC-(?:PASS|NO-NOVELTY|NO-CLAIM|DEFERRED)\b", cells[8])
        if len(statuses) != 1:
            raise FinalFiguresError(f"final claim status is invalid: {cells[0]}")
        prior = re.search(r"`(SUBSUMED|CLOSE_PRIOR|PARTIAL_GAP|PLAUSIBLE_GAP|UNRESOLVED)`", cells[2])
        if prior is None:
            raise FinalFiguresError(f"prior-art status is missing: {cells[0]}")
        rows.append(
            {
                "claim_id": cells[0],
                "final_status": statuses[0],
                "prior_art_status": prior.group(1),
                "statistical_status": next(
                    (status for status in ("S-PASS", "S-FAIL", "S-NOT-APPLICABLE") if status in cells[8]),
                    "MISSING",
                ),
                "supported_claim": "NO" if statuses[0] != "C-PASS" else "YES",
            }
        )
    if [row["claim_id"] for row in rows] != EXPECTED_CLAIMS:
        raise FinalFiguresError("Claim Matrix identities or order drifted")
    return rows


def _csv_bytes(rows: list[dict[str, Any]], fields: list[str]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def _svg_root(width: int, height: int, title: str, subtitle: str) -> ET.Element:
    ET.register_namespace("", SVG_NS)
    root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {"width": str(width), "height": str(height), "viewBox": f"0 0 {width} {height}"},
    )
    ET.SubElement(root, f"{{{SVG_NS}}}rect", {"width": "100%", "height": "100%", "fill": "#ffffff"})
    _text(root, 48, 58, title, 28, "#17202a", "700")
    _text(root, 48, 90, subtitle, 16, "#4d5656")
    return root


def _text(
    root: ET.Element,
    x: float,
    y: float,
    value: str,
    size: int = 14,
    color: str = "#263238",
    weight: str = "400",
    anchor: str = "start",
) -> None:
    element = ET.SubElement(
        root,
        f"{{{SVG_NS}}}text",
        {
            "x": f"{x:.2f}",
            "y": f"{y:.2f}",
            "font-family": "Arial, sans-serif",
            "font-size": str(size),
            "font-weight": weight,
            "fill": color,
            "text-anchor": anchor,
        },
    )
    element.text = value


def _svg_bytes(root: ET.Element) -> bytes:
    rendered = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    if not isinstance(rendered, bytes):
        raise FinalFiguresError("SVG renderer returned text instead of bytes")
    return rendered


def render_routebench_svg(rows: list[dict[str, Any]]) -> bytes:
    root = _svg_root(
        1400,
        1320,
        "R3-327 Statistical RouteBench pilot",
        "Candidate minus comparator; n=8 paired units per cell; descriptive only; confirmatory inference not executed",
    )
    panels = [
        ("scenario_risk_index", 145, -0.30, 0.02, "Unitless paired risk-index difference"),
        ("assignment_rate", 730, -0.025, 0.01, "Assignment-rate difference (proportion)"),
    ]
    for metric_id, top, minimum, maximum, label in panels:
        selected = [row for row in rows if row["metric_id"] == metric_id]
        left, right = 330.0, 1320.0
        _text(root, 48, top, label, 20, "#17202a", "700")
        axis_y = top + 50
        ET.SubElement(
            root,
            f"{{{SVG_NS}}}line",
            {"x1": str(left), "x2": str(right), "y1": str(axis_y), "y2": str(axis_y), "stroke": "#85929e"},
        )
        for index in range(6):
            value = minimum + (maximum - minimum) * index / 5
            x = left + (right - left) * index / 5
            ET.SubElement(
                root,
                f"{{{SVG_NS}}}line",
                {"x1": str(x), "x2": str(x), "y1": str(axis_y - 5), "y2": str(axis_y + 430), "stroke": "#e5e8e8"},
            )
            _text(root, x, axis_y - 12, f"{value:.3f}", 12, "#566573", anchor="middle")
        zero_x = left + (0 - minimum) / (maximum - minimum) * (right - left)
        ET.SubElement(
            root,
            f"{{{SVG_NS}}}line",
            {"x1": str(zero_x), "x2": str(zero_x), "y1": str(axis_y), "y2": str(axis_y + 430), "stroke": "#17202a", "stroke-width": "2"},
        )
        for index, row in enumerate(selected):
            y = axis_y + 45 + index * 48
            _text(root, 48, y + 5, row["regime_id"], 14, "#263238")
            if row["status"] == "NON_ESTIMABLE":
                ET.SubElement(
                    root,
                    f"{{{SVG_NS}}}rect",
                    {"x": str(left), "y": str(y - 13), "width": str(right - left), "height": "25", "fill": "#fdf2e9"},
                )
                _text(root, left + 12, y + 5, "NON-ESTIMABLE: zero paired variance / power", 13, "#a04000", "700")
                continue
            low_x = left + (row["ci95_lower"] - minimum) / (maximum - minimum) * (right - left)
            high_x = left + (row["ci95_upper"] - minimum) / (maximum - minimum) * (right - left)
            mean_x = left + (row["mean_difference"] - minimum) / (maximum - minimum) * (right - left)
            ET.SubElement(
                root,
                f"{{{SVG_NS}}}line",
                {"x1": str(low_x), "x2": str(high_x), "y1": str(y), "y2": str(y), "stroke": "#2471a3", "stroke-width": "4"},
            )
            ET.SubElement(
                root,
                f"{{{SVG_NS}}}circle",
                {"cx": str(mean_x), "cy": str(y), "r": "7", "fill": "#c0392b"},
            )
            _text(root, right - 8, y + 5, f"{row['mean_difference']:.4f} [{row['ci95_lower']:.4f}, {row['ci95_upper']:.4f}]", 12, "#17202a", anchor="end")
    _text(root, 48, 1255, "All 16 cells retained; no exclusions. Six assignment cells are explicitly non-estimable.", 15, "#922b21", "700")
    _text(root, 48, 1285, "Intervals are unadjusted pilot descriptions; Holm-family p-values are null because no confirmatory campaign ran.", 14, "#4d5656")
    return _svg_bytes(root)


def render_support_svg(rows: list[dict[str, Any]]) -> bytes:
    root = _svg_root(
        1400,
        930,
        "R3-336 / R3-349 evidence support",
        "Observed records or paired units versus frozen support requirements; unsupported states are retained",
    )
    headers = [(48, "Task / category"), (510, "Observed / required"), (760, "Status"), (1160, "Uncertainty")]
    for x, value in headers:
        _text(root, x, 135, value, 15, "#17202a", "700")
    for index, row in enumerate(rows):
        y = 178 + index * 58
        fill = "#f4f6f7" if index % 2 == 0 else "#ffffff"
        ET.SubElement(root, f"{{{SVG_NS}}}rect", {"x": "35", "y": str(y - 31), "width": "1330", "height": "49", "fill": fill})
        _text(root, 48, y, f"{row['task_id']} / {row['category']}", 13)
        requirement = row["required"] if isinstance(row["required"], int) else "held-out data"
        unit = "paired units" if isinstance(row["required"], int) else "records"
        _text(root, 510, y, f"{row['observed']} / {requirement} ({unit})", 13)
        _text(root, 760, y, row["status"], 12, "#a04000", "700")
        _text(root, 1160, y, row["uncertainty"], 11, "#566573")
    _text(root, 48, 890, "No row was excluded. Twin: zero records. RADS: no variant outcomes; location-noise regime absent; 8 < 30 pairs.", 14, "#922b21", "700")
    return _svg_bytes(root)


def render_claim_svg(rows: list[dict[str, str]]) -> bytes:
    statuses = ["C-PASS", "C-NO-NOVELTY", "C-NO-CLAIM", "C-DEFERRED"]
    counts = {status: sum(row["final_status"] == status for row in rows) for status in statuses}
    root = _svg_root(
        1100,
        760,
        "R3-359 final claim dispositions",
        "Unit: Claim Matrix row count; categorical review has no statistical uncertainty",
    )
    left, bottom, chart_height = 120.0, 630.0, 440.0
    ET.SubElement(root, f"{{{SVG_NS}}}line", {"x1": str(left), "x2": "1040", "y1": str(bottom), "y2": str(bottom), "stroke": "#17202a", "stroke-width": "2"})
    for tick in range(8):
        y = bottom - chart_height * tick / 7
        ET.SubElement(root, f"{{{SVG_NS}}}line", {"x1": str(left), "x2": "1040", "y1": str(y), "y2": str(y), "stroke": "#e5e8e8"})
        _text(root, left - 18, y + 5, str(tick), 12, "#566573", anchor="end")
    colors = ["#1e8449", "#2471a3", "#a04000", "#7d3c98"]
    for index, status in enumerate(statuses):
        x = 205 + index * 220
        count = counts[status]
        height = chart_height * count / 7
        ET.SubElement(root, f"{{{SVG_NS}}}rect", {"x": str(x), "y": str(bottom - height), "width": "120", "height": str(height), "fill": colors[index]})
        _text(root, x + 60, bottom - height - 18, str(count), 24, colors[index], "700", "middle")
        _text(root, x + 60, bottom + 34, status, 13, "#263238", "700", "middle")
    _text(root, 48, 720, "Supported scientific claims: NONE. Formatting and reproduction do not promote an unsupported row.", 16, "#922b21", "700")
    return _svg_bytes(root)


def _write_once(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise FinalFiguresError(f"write-once artifact collision: {path}")
    else:
        path.write_bytes(data)
    sidecar = path.with_name(f"{path.name}.sha256")
    sidecar_data = f"{_sha256_bytes(data)}\n".encode("ascii")
    if sidecar.exists() and sidecar.read_bytes() != sidecar_data:
        raise FinalFiguresError(f"write-once sidecar collision: {sidecar}")
    if not sidecar.exists():
        sidecar.write_bytes(sidecar_data)


def _write_repository(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def generate(plan_path: Path, repo_root: Path, data_root: Path) -> dict[str, Any]:
    plan = _json(plan_path)
    validate_plan(plan)
    sources = _verify_repository_sources(plan, repo_root)
    report = _verify_external_report(plan, data_root)
    routebench_rows = extract_routebench_cells(report)
    support_rows = build_support_rows(
        sources["twin_manifest"], sources["rads_manifest"], sources["independent_reproduction"]
    )
    claim_rows = extract_claim_rows(sources["claim_matrix"])

    routebench_csv = _csv_bytes(routebench_rows, list(routebench_rows[0]))
    support_csv = _csv_bytes(support_rows, list(support_rows[0]))
    claims_csv = _csv_bytes(claim_rows, list(claim_rows[0]))
    artifacts = {
        "routebench-pilot-intervals.svg": render_routebench_svg(routebench_rows),
        "evidence-support-status.svg": render_support_svg(support_rows),
        "claim-dispositions.svg": render_claim_svg(claim_rows),
        "routebench-cells.csv": routebench_csv,
        "evidence-support.csv": support_csv,
        "claim-dispositions.csv": claims_csv,
    }
    repository_root = _resolve_below(repo_root, plan["output"]["repository_relative_root"])
    external_root = _resolve_below(data_root, plan["output"]["external_relative_root"])
    for name, data in artifacts.items():
        _write_repository(repository_root / name, data)
        _write_once(external_root / name, data)

    index: dict[str, Any] = {
        "schema_version": "routemind-final-scientific-figures-index-v1",
        "task_id": "R3-360",
        "plan_id": plan["plan_id"],
        "plan_digest": plan["plan_digest"],
        "source_lineage": {
            source_id: {
                "scope": source["scope"],
                "relative_path": source["relative_path"],
                "byte_sha256": source["byte_sha256"],
                **({"content_digest": source["content_digest"]} if "content_digest" in source else {}),
            }
            for source_id, source in plan["sources"].items()
        },
        "row_counts": {"routebench_cells": 16, "evidence_support": 12, "claim_dispositions": 7},
        "negative_outcomes": {
            "routebench_non_estimable_cells": 6,
            "confirmatory_inference": "NOT_EXECUTED",
            "twin_observed_records": 0,
            "rads_unsupported_axes": ["location_noise"],
            "c_pass_claims": 0,
            "excluded_rows": 0,
        },
        "artifacts": [
            {
                "file": name,
                "bytes": len(data),
                "sha256": _sha256_bytes(data),
                "repository_relative_path": str(
                    Path(plan["output"]["repository_relative_root"]) / name
                ).replace("\\", "/"),
                "external_relative_path": str(
                    Path(plan["output"]["external_relative_root"]) / name
                ).replace("\\", "/"),
            }
            for name, data in sorted(artifacts.items())
        ],
        "claim_boundary": plan["claim_boundary"],
    }
    index["bundle_digest"] = _canonical_digest(index, "bundle_digest")
    index_bytes = (json.dumps(index, indent=2, sort_keys=True) + "\n").encode("utf-8")
    index_name = plan["output"]["index_file"]
    _write_repository(repository_root / index_name, index_bytes)
    _write_once(external_root / index_name, index_bytes)
    return index


def validate_committed(plan_path: Path, repo_root: Path) -> dict[str, Any]:
    plan = _json(plan_path)
    validate_plan(plan)
    _verify_repository_sources(plan, repo_root)
    repository_root = _resolve_below(repo_root, plan["output"]["repository_relative_root"])
    index = _json(repository_root / plan["output"]["index_file"])
    if index.get("schema_version") != "routemind-final-scientific-figures-index-v1":
        raise FinalFiguresError("final figure index schema drifted")
    if index.get("plan_digest") != plan["plan_digest"]:
        raise FinalFiguresError("final figure plan linkage drifted")
    if index.get("bundle_digest") != _canonical_digest(index, "bundle_digest"):
        raise FinalFiguresError("final figure bundle digest mismatch")
    artifacts = index.get("artifacts", [])
    if len(artifacts) != 6:
        raise FinalFiguresError("final artifact inventory drifted")
    for artifact in artifacts:
        path = _resolve_below(repo_root, artifact["repository_relative_path"])
        if path.stat().st_size != artifact["bytes"] or _sha256_file(path) != artifact["sha256"]:
            raise FinalFiguresError(f"committed final artifact drifted: {artifact['file']}")
    expected_negative = {
        "routebench_non_estimable_cells": 6,
        "confirmatory_inference": "NOT_EXECUTED",
        "twin_observed_records": 0,
        "rads_unsupported_axes": ["location_noise"],
        "c_pass_claims": 0,
        "excluded_rows": 0,
    }
    if index.get("negative_outcomes") != expected_negative:
        raise FinalFiguresError("negative-outcome summary drifted")
    return {
        "valid": True,
        "plan_digest": plan["plan_digest"],
        "bundle_digest": index["bundle_digest"],
        "artifact_count": len(artifacts),
        "row_counts": index["row_counts"],
        "negative_outcomes": index["negative_outcomes"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, default=PLAN_PATH)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--generate", action="store_true")
    args = parser.parse_args()
    try:
        if args.generate:
            if args.data_root is None:
                parser.error("--data-root is required with --generate")
            result = generate(args.plan, args.repo_root, args.data_root)
        else:
            result = validate_committed(args.plan, args.repo_root)
    except FinalFiguresError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
