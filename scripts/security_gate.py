from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".jks"}
PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")
TOKEN_PATTERNS = (
    re.compile(r"\b(?:gh[pousr]|github_pat)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
)
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(?:api[_-]?key|private[_-]?key|secret[_-]?key|access[_-]?token)"
    r"\s*[:=]\s*[\"']?([A-Za-z0-9/+_=.-]{16,})"
)
PLACEHOLDER_PATTERN = re.compile(
    r"(?i)(?:change-me|local-only|placeholder|example|sample|dummy|test-only|\$\{|<[^>]+>)"
)


def tracked_files(root: Path = ROOT) -> tuple[Path, ...]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return tuple(root / item for item in result.stdout.decode("utf-8").split("\0") if item)


def scan_text(path: Path, text: str) -> list[str]:
    findings: list[str] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if PRIVATE_KEY_PATTERN.search(line):
            findings.append(f"{path}:{line_number}: private key material")
        if any(pattern.search(line) for pattern in TOKEN_PATTERNS):
            findings.append(f"{path}:{line_number}: high-confidence provider token")
        assignment = SECRET_ASSIGNMENT_PATTERN.search(line)
        if assignment and not PLACEHOLDER_PATTERN.search(assignment.group(1)):
            findings.append(f"{path}:{line_number}: non-placeholder secret assignment")
    return findings


def check_tracked_files(files: tuple[Path, ...]) -> list[str]:
    findings: list[str] = []
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        name = path.name.lower()
        if name == ".env" or (
            name.startswith(".env.") and name not in {".env.example", ".env.template"}
        ):
            findings.append(f"{relative}: environment secret file is tracked")
        if path.suffix.lower() in SENSITIVE_SUFFIXES:
            findings.append(f"{relative}: sensitive key-file extension is tracked")
        try:
            content = path.read_bytes()
        except OSError as error:
            findings.append(f"{relative}: cannot read tracked file: {error}")
            continue
        if b"\0" not in content:
            findings.extend(scan_text(Path(relative), content.decode("utf-8", errors="replace")))
    return findings


def check_lockfiles() -> list[str]:
    findings: list[str] = []
    uv_lock = ROOT / "services" / "compute-api" / "uv.lock"
    if not uv_lock.is_file():
        findings.append("services/compute-api/uv.lock: lockfile is missing")
    else:
        header = uv_lock.read_text(encoding="utf-8")[:512]
        if "version = 1" not in header or "revision =" not in header:
            findings.append("services/compute-api/uv.lock: invalid uv lock header")

    npm_lock = ROOT / "apps" / "web" / "package-lock.json"
    if not npm_lock.is_file():
        findings.append("apps/web/package-lock.json: lockfile is missing")
    else:
        try:
            payload = json.loads(npm_lock.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            findings.append(f"apps/web/package-lock.json: invalid JSON: {error}")
        else:
            if payload.get("lockfileVersion", 0) < 3 or "packages" not in payload:
                findings.append("apps/web/package-lock.json: expected npm lockfile v3 metadata")
    return findings


def check_workflows() -> list[str]:
    findings: list[str] = []
    workflows = tuple(WORKFLOW_DIR.glob("*.yml")) + tuple(WORKFLOW_DIR.glob("*.yaml"))
    if not workflows:
        return [".github/workflows: no workflow files found"]
    for path in workflows:
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT).as_posix()
        if "permissions:" not in text:
            findings.append(f"{relative}: permissions must be explicit")
        if not re.search(r"(?m)^\s+contents:\s*read\s*$", text):
            findings.append(f"{relative}: contents: read permission is required")
        if re.search(r"(?i)permissions:\s*write-all|\bid-token:\s*write\b", text):
            findings.append(f"{relative}: broad or token-minting permission is forbidden")
        if re.search(r"(?i)^\s+pull-requests:\s*write\s*$", text, re.MULTILINE):
            findings.append(f"{relative}: pull-request write permission is forbidden")
    return findings


def check_supply_chain_automation() -> list[str]:
    findings: list[str] = []
    required_files = (
        "scripts/supply-chain.ps1",
        "scripts/supply_chain_evidence.py",
        "scripts/supply_chain_evidence_test.py",
    )
    findings.extend(f"{relative}: supply-chain automation is missing" for relative in required_files if not (ROOT / relative).is_file())
    workflow = WORKFLOW_DIR / "ci.yml"
    if not workflow.is_file():
        return findings + [".github/workflows/ci.yml: supply-chain workflow is missing"]
    text = workflow.read_text(encoding="utf-8")
    markers = {
        "./scripts/supply-chain.ps1": "SBOM and provenance generation step",
        "actions/upload-artifact@v7": "supply-chain artifact retention step",
        "if-no-files-found: error": "missing-artifact failure policy",
        "retention-days: 30": "bounded artifact retention policy",
    }
    findings.extend(
        f".github/workflows/ci.yml: missing {description}"
        for marker, description in markers.items()
        if marker not in text
    )
    return findings


def check_compose() -> list[str]:
    compose = ROOT / "compose.yaml"
    if not compose.is_file():
        return ["compose.yaml: file is missing"]
    text = compose.read_text(encoding="utf-8")
    findings: list[str] = []
    if re.search(r"(?m)^\s*image:\s*[^\n:]+:latest\s*$", text):
        findings.append("compose.yaml: latest image tags are forbidden")
    for line_number, line in enumerate(text.splitlines(), 1):
        if re.search(r"(?m)^\s*-\s*[\"'](?!127\.0\.0\.1:)[^\"']+:[^\"']+[\"']\s*$", line):
            findings.append(f"compose.yaml:{line_number}: service ports must bind to loopback")
    if "change-me-local-only" not in text:
        findings.append("compose.yaml: local-only credential placeholder is missing")
    return findings


def validate() -> list[str]:
    try:
        files = tracked_files()
    except (OSError, subprocess.CalledProcessError) as error:
        return [f"git tracked-file listing failed: {error}"]
    findings = check_tracked_files(files)
    findings.extend(check_lockfiles())
    findings.extend(check_workflows())
    findings.extend(check_supply_chain_automation())
    findings.extend(check_compose())
    if not any(path.relative_to(ROOT).as_posix() == ".env.example" for path in files):
        findings.append(".env.example: committed local configuration example is missing")
    return findings


def main() -> int:
    findings = validate()
    if findings:
        for finding in findings:
            print(f"ERROR: {finding}", file=sys.stderr)
        return 1
    print("PASS: tracked secret isolation")
    print("PASS: dependency lockfile metadata")
    print("PASS: workflow least-privilege permissions")
    print("PASS: SBOM and provenance automation")
    print("PASS: Compose image and loopback hygiene")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
