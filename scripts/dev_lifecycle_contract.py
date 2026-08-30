from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dev-up.ps1"


def validate() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    required = (
        'ValidateSet("check", "up", "status", "down")',
        "Invoke-Check",
        "Invoke-Up",
        "Invoke-Down",
        "Wait-Endpoint",
        "Wait-ComposeHealthy",
        "Ensure-EnvironmentFile",
        "api-readiness",
        "web-readiness",
        "Stop-TrackedState",
        "persistent development volumes were preserved",
        '"routemind-local-runtime.v1"',
        '"business-api"',
        '"compute-api"',
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise AssertionError(f"dev-up.ps1 is missing lifecycle markers: {missing}")
    if "docker compose down -v" in text:
        raise AssertionError("dev-up.ps1 must not delete persistent volumes")


if __name__ == "__main__":
    validate()
    print("PASS: bounded local lifecycle contract")
