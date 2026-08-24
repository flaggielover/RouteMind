from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from .reason_codes import ResearchGateError

PROTOCOL_ID = "gate2b-stochastic-equilibrium-v1"
PROTOCOL_JSON = "GATE2B_STOCHASTIC_EQUILIBRIUM_PREREGISTRATION.json"
PROTOCOL_MD = "GATE2B_STOCHASTIC_EQUILIBRIUM_PREREGISTRATION.md"
PROTOCOL_JSON_SHA256 = (
    "aac5da0419b77bf76e8740dc7cc7ed2cff232f1b3299e1395d2bace60697dd26"
)
PROTOCOL_MD_SHA256 = "5f034cc83f7dae1a826a227e8b8a90a33fee140a214d0873d1aa0bec933d9657"


def _sha256(path: Path) -> str:
    if not path.is_file():
        raise ResearchGateError("GATE2B_FROZEN_INPUT_MISMATCH", str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sidecar_digest(path: Path) -> str:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not sidecar.is_file():
        raise ResearchGateError("GATE2B_FROZEN_INPUT_MISMATCH", str(sidecar))
    try:
        return sidecar.read_text(encoding="ascii").split(maxsplit=1)[0]
    except (OSError, IndexError) as exc:
        raise ResearchGateError("GATE2B_FROZEN_INPUT_MISMATCH", str(sidecar)) from exc


def _mapping(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ResearchGateError("GATE2B_FROZEN_INPUT_MISMATCH", name)
    return cast(dict[str, object], value)


@dataclass(frozen=True, slots=True)
class Gate2bProtocol:
    path: Path
    payload: dict[str, object]
    sha256: str

    def section(self, name: str) -> dict[str, object]:
        return _mapping(self.payload.get(name), name)


def load_gate2b_protocol(package_root: Path) -> Gate2bProtocol:
    reports = package_root / "reports"
    json_path = reports / PROTOCOL_JSON
    markdown_path = reports / PROTOCOL_MD
    observed_json = _sha256(json_path)
    observed_markdown = _sha256(markdown_path)
    checks = (
        (observed_json, PROTOCOL_JSON_SHA256, json_path),
        (_sidecar_digest(json_path), PROTOCOL_JSON_SHA256, json_path),
        (observed_markdown, PROTOCOL_MD_SHA256, markdown_path),
        (_sidecar_digest(markdown_path), PROTOCOL_MD_SHA256, markdown_path),
    )
    for observed, expected, path in checks:
        if observed != expected:
            raise ResearchGateError(
                "GATE2B_FROZEN_INPUT_MISMATCH",
                f"{path.name}: expected {expected}, observed {observed}",
            )
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ResearchGateError("GATE2B_FROZEN_INPUT_MISMATCH", str(exc)) from exc
    if not isinstance(payload, dict):
        raise ResearchGateError(
            "GATE2B_FROZEN_INPUT_MISMATCH", "protocol root is not an object"
        )
    typed = cast(dict[str, object], payload)
    if typed.get("schema_version") != 1 or typed.get("protocol_id") != PROTOCOL_ID:
        raise ResearchGateError(
            "GATE2B_FROZEN_INPUT_MISMATCH", "protocol identity changed"
        )
    threshold = _mapping(typed.get("threshold_gate"), "threshold_gate")
    if (
        threshold.get("relative_prediction_error_max") != 0.01
        or threshold.get("relative_transition_width_max") != 0.025
        or threshold.get("identification_interval_overlap_is_pass_condition")
        is not False
        or threshold.get("identification_interval_overlap_role")
        != "SUPPLEMENTARY_CORRESPONDENCE_DIAGNOSTIC_ONLY"
    ):
        raise ResearchGateError(
            "GATE2B_FROZEN_INPUT_MISMATCH", "threshold Gate changed"
        )
    controls = _mapping(typed.get("synthetic_controls"), "synthetic_controls")
    if (
        controls.get("strict_split") is not True
        or controls.get("holdout_unreadable_until_calibration_frozen_pass") is not True
        or controls.get("classifier_changes_after_freeze") is not False
        or controls.get("classifier_changes_after_holdout") is not False
    ):
        raise ResearchGateError(
            "GATE2B_FROZEN_INPUT_MISMATCH", "control isolation changed"
        )
    historical = _mapping(typed.get("frozen_inputs"), "frozen_inputs")
    expected_files = {
        "FROZEN_THRESHOLD_PREDICTION.md": "frozen_threshold_report_sha256",
        "GATE2_TRANSITION_DEFINITION.md": "gate2_definition_sha256",
        "GATE2_LONG_HORIZON_VALIDATION.md": "gate2_report_sha256",
        "GATE2_VALIDATION_SUMMARY.json": "gate2_summary_sha256",
        "NEGATIVE_CONTROL_DIAGNOSTIC_PREREGISTRATION.md": (
            "diagnostic_preregistration_sha256"
        ),
        "NEGATIVE_CONTROL_DIAGNOSTIC_REPORT.md": "diagnostic_report_sha256",
        "NEGATIVE_CONTROL_DIAGNOSTIC_SUMMARY.json": "diagnostic_summary_sha256",
    }
    for filename, key in expected_files.items():
        expected_value = historical.get(key)
        if (
            not isinstance(expected_value, str)
            or _sha256(reports / filename) != expected_value
        ):
            raise ResearchGateError(
                "GATE2B_FROZEN_INPUT_MISMATCH", f"{filename} changed"
            )
    main_digest = historical.get("main_preregistration_content_digest")
    frozen_digest = (
        (package_root / "configs" / "preregistration.sha256")
        .read_text(encoding="ascii")
        .split(maxsplit=1)[0]
    )
    if main_digest != frozen_digest:
        raise ResearchGateError(
            "GATE2B_FROZEN_INPUT_MISMATCH", "main preregistration changed"
        )
    return Gate2bProtocol(json_path.resolve(), typed, observed_json)
