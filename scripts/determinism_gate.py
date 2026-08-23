from __future__ import annotations

import json
import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1] / "services" / "compute-api"
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from routemind_compute.application.determinism import audit_scenario  # noqa: E402
from routemind_compute.application.registry import default_registry  # noqa: E402
from routemind_compute.application.simulation import (  # noqa: E402
    CourierState,
    DemandEvent,
    ScenarioKernel,
    ScenarioManifest,
)
from routemind_compute.application.travel import DeterministicLocalTravelProvider  # noqa: E402
from routemind_compute.domain.dispatch import GeoPoint  # noqa: E402


def main() -> int:
    manifest = ScenarioManifest(
        "determinism-gate",
        20260823,
        (
            DemandEvent("demand-1", GeoPoint(31.2304, 121.4737), 0),
            DemandEvent("demand-2", GeoPoint(31.2314, 121.4747), 2),
        ),
        (CourierState("courier-1", GeoPoint(31.2300, 121.4730)),),
        delay_ticks=(0, 1),
    )
    kernel = ScenarioKernel(
        default_registry(), DeterministicLocalTravelProvider(), strategy="nearest"
    )
    audit = audit_scenario(manifest, kernel.run, configuration=(("gate", "ci"),))
    print(json.dumps(audit.evidence(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
