from __future__ import annotations

import os
import platform
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from routemind_compute.application.parameters import Metadata
from routemind_compute.application.simulation import ScenarioManifest, ScenarioRun

DeterminismClass = Literal[
    "DETERMINISM_CRITICAL",
    "DETERMINISTIC_IF_CONFIGURED",
    "NONDETERMINISTIC_ALLOWED",
]


@dataclass(frozen=True, slots=True)
class DeterminismContract:
    subsystem: str
    classification: DeterminismClass
    comparison: Literal["digest", "observational"] = "digest"

    def __post_init__(self) -> None:
        if not self.subsystem.strip():
            raise ValueError("determinism subsystem must not be blank")
        if self.classification not in {
            "DETERMINISM_CRITICAL",
            "DETERMINISTIC_IF_CONFIGURED",
            "NONDETERMINISTIC_ALLOWED",
        }:
            raise ValueError("unsupported determinism classification")


DEFAULT_CONTRACTS: tuple[DeterminismContract, ...] = (
    DeterminismContract("scenario-kernel", "DETERMINISM_CRITICAL"),
    DeterminismContract("routebench", "DETERMINISM_CRITICAL"),
    DeterminismContract("routebench-crn", "DETERMINISM_CRITICAL"),
    DeterminismContract("routebench-statistics", "DETERMINISM_CRITICAL"),
    DeterminismContract("rads", "DETERMINISTIC_IF_CONFIGURED"),
    DeterminismContract("api-observability", "NONDETERMINISTIC_ALLOWED", "observational"),
)


@dataclass(frozen=True, slots=True)
class ReproducibilityAudit:
    contract: DeterminismContract
    seed: int
    configuration: Metadata
    environment: Metadata
    first_digest: str
    second_digest: str

    @property
    def stable(self) -> bool:
        return self.first_digest == self.second_digest

    def evidence(self) -> dict[str, object]:
        return {
            "subsystem": self.contract.subsystem,
            "classification": self.contract.classification,
            "comparison": self.contract.comparison,
            "seed": self.seed,
            "configuration": self.configuration,
            "environment": self.environment,
            "first_digest": self.first_digest,
            "second_digest": self.second_digest,
            "stable": self.stable,
        }


class DeterminismViolationError(RuntimeError):
    def __init__(self, audit: ReproducibilityAudit) -> None:
        self.audit = audit
        super().__init__(
            f"determinism contract failed for {audit.contract.subsystem}: "
            f"{audit.first_digest} != {audit.second_digest}"
        )


def environment_metadata() -> Metadata:
    """Return the bounded runtime facts needed to interpret a digest."""
    return (
        ("implementation", platform.python_implementation()),
        ("python_version", platform.python_version()),
        ("platform", sys.platform),
        ("hash_seed", os.environ.get("PYTHONHASHSEED", "randomized")),
    )


def contract_for(subsystem: str) -> DeterminismContract:
    for contract in DEFAULT_CONTRACTS:
        if contract.subsystem == subsystem:
            return contract
    raise KeyError(f"unknown determinism subsystem: {subsystem}")


def audit_scenario(
    manifest: ScenarioManifest,
    runner: Callable[[ScenarioManifest], ScenarioRun],
    *,
    subsystem: str = "scenario-kernel",
    configuration: Metadata = (),
    contract: DeterminismContract | None = None,
    environment: Metadata | None = None,
) -> ReproducibilityAudit:
    """Run the same seeded scenario twice and enforce its declared contract."""
    selected_contract = contract or contract_for(subsystem)
    normalized_configuration = tuple(sorted(configuration))
    normalized_environment = tuple(sorted(environment or environment_metadata()))
    first = runner(manifest)
    second = runner(manifest)
    audit = ReproducibilityAudit(
        selected_contract,
        manifest.seed,
        normalized_configuration,
        normalized_environment,
        first.replay_digest,
        second.replay_digest,
    )
    if not audit.stable and selected_contract.classification in {
        "DETERMINISM_CRITICAL",
        "DETERMINISTIC_IF_CONFIGURED",
    }:
        raise DeterminismViolationError(audit)
    return audit
