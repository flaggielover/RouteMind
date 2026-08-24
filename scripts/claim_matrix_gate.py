from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "docs" / "research" / "r3" / "CLAIM_MATRIX.md"
EXPECTED_STATUSES = {
    "R3-A1": "C-NO-CLAIM",
    "R3-A2": "C-NO-NOVELTY",
    "R3-B1": "C-NO-CLAIM",
    "R3-C1": "C-NO-CLAIM",
    "R3-D1": "C-NO-CLAIM",
    "R3-D2": "C-NO-CLAIM",
    "R3-E1": "C-NO-NOVELTY",
}
ALLOWED_FINAL_STATUSES = {
    "C-PASS",
    "C-NO-NOVELTY",
    "C-NO-CLAIM",
    "C-DEFERRED",
}
REQUIRED_HEADERS = [
    "Claim ID",
    "Hypothesis",
    "Prior art",
    "Dataset/scenario",
    "Manifest",
    "Primary metric/test",
    "Effect/uncertainty gate",
    "Independent verification/reproduction",
    "Final gates",
    "Final wording",
]


class ClaimMatrixError(ValueError):
    pass


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _section(text: str, heading: str) -> str:
    pattern = rf"(?ms)^## {re.escape(heading)}\s*$\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text)
    if match is None:
        raise ClaimMatrixError(f"missing section: {heading}")
    return match.group(1).strip()


def validate_claim_matrix(text: str) -> dict[str, object]:
    lines = text.splitlines()
    try:
        header_index = next(
            index for index, line in enumerate(lines) if line.startswith("| Claim ID |")
        )
    except StopIteration as exc:
        raise ClaimMatrixError("missing claim table") from exc

    headers = _cells(lines[header_index])
    if headers != REQUIRED_HEADERS:
        raise ClaimMatrixError("claim table headers drifted")
    if header_index + 1 >= len(lines) or not lines[header_index + 1].startswith("| ---"):
        raise ClaimMatrixError("missing claim table separator")

    rows: dict[str, list[str]] = {}
    for line in lines[header_index + 2 :]:
        if not line.startswith("| R3-"):
            break
        cells = _cells(line)
        if len(cells) != len(REQUIRED_HEADERS):
            raise ClaimMatrixError("claim row has the wrong column count")
        claim_id = cells[0]
        if claim_id in rows:
            raise ClaimMatrixError(f"duplicate claim row: {claim_id}")
        if any(not cell for cell in cells):
            raise ClaimMatrixError(f"empty claim field: {claim_id}")
        rows[claim_id] = cells

    if set(rows) != set(EXPECTED_STATUSES):
        raise ClaimMatrixError("claim identities do not match the frozen seven-row review")

    statuses: dict[str, str] = {}
    for claim_id, cells in rows.items():
        status_matches = re.findall(r"\bC-[A-Z-]+\b", cells[8])
        if len(status_matches) != 1:
            raise ClaimMatrixError(f"{claim_id}: final gates must contain one C status")
        status = status_matches[0]
        if status not in ALLOWED_FINAL_STATUSES:
            raise ClaimMatrixError(f"{claim_id}: non-final claim status {status}")
        if status != EXPECTED_STATUSES[claim_id]:
            raise ClaimMatrixError(f"{claim_id}: final claim disposition drifted")
        if "R3-357 PA-" not in cells[2]:
            raise ClaimMatrixError(f"{claim_id}: prior-art audit identity is missing")
        if "R3-356" not in cells[7]:
            raise ClaimMatrixError(f"{claim_id}: reproduction disposition is missing")
        statuses[claim_id] = status

    supported_section = _section(text, "Supported scientific claims")
    supported_ids = set(re.findall(r"\bR3-[A-Z]\d\b", supported_section))
    c_pass_ids = {claim_id for claim_id, status in statuses.items() if status == "C-PASS"}
    if supported_ids != c_pass_ids:
        raise ClaimMatrixError("supported-claims section does not match C-PASS rows")
    if not c_pass_ids and supported_section != "None.":
        raise ClaimMatrixError("zero C-PASS rows require an explicit None supported section")

    if "R3-325 remains frozen exactly as" not in text:
        raise ClaimMatrixError("R3-325 frozen boundary is missing")
    if "E-PASS / X-PASS / S-FAIL / C-NO-CLAIM" not in text:
        raise ClaimMatrixError("R3-325 frozen scientific outcome drifted")

    return {
        "valid": True,
        "matrix_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "claim_count": len(rows),
        "c_pass_count": sum(status == "C-PASS" for status in statuses.values()),
        "c_no_novelty_count": sum(
            status == "C-NO-NOVELTY" for status in statuses.values()
        ),
        "c_no_claim_count": sum(
            status == "C-NO-CLAIM" for status in statuses.values()
        ),
        "c_deferred_count": sum(status == "C-DEFERRED" for status in statuses.values()),
    }


def main() -> int:
    try:
        result = validate_claim_matrix(MATRIX_PATH.read_text(encoding="utf-8"))
    except (OSError, ClaimMatrixError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
