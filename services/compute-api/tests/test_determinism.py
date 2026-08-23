from dataclasses import replace

import pytest

from routemind_compute.application.determinism import (
    DEFAULT_CONTRACTS,
    DeterminismContract,
    DeterminismViolationError,
    ReproducibilityAudit,
    audit_scenario,
    contract_for,
    environment_metadata,
)
from routemind_compute.application.registry import default_registry
from routemind_compute.application.simulation import (
    CourierState,
    DemandEvent,
    ScenarioKernel,
    ScenarioManifest,
    ScenarioRun,
)
from routemind_compute.application.travel import DeterministicLocalTravelProvider
from routemind_compute.domain.dispatch import GeoPoint


def manifest() -> ScenarioManifest:
    return ScenarioManifest(
        "determinism-test",
        7,
        (DemandEvent("demand-1", GeoPoint(31.23, 121.47), 0),),
        (CourierState("courier-1", GeoPoint(31.231, 121.471)),),
    )


def kernel() -> ScenarioKernel:
    return ScenarioKernel(default_registry(), DeterministicLocalTravelProvider())


def test_contract_catalog_and_environment_are_explicit() -> None:
    assert {item.classification for item in DEFAULT_CONTRACTS} == {
        "DETERMINISM_CRITICAL",
        "DETERMINISTIC_IF_CONFIGURED",
        "NONDETERMINISTIC_ALLOWED",
    }
    assert contract_for("scenario-kernel").classification == "DETERMINISM_CRITICAL"
    assert {key for key, _ in environment_metadata()} == {
        "implementation",
        "python_version",
        "platform",
        "hash_seed",
    }
    with pytest.raises(KeyError):
        contract_for("missing")
    with pytest.raises(ValueError):
        DeterminismContract("", "DETERMINISM_CRITICAL")
    with pytest.raises(ValueError):
        DeterminismContract("bad", "unknown")  # type: ignore[arg-type]


def test_audit_repeats_seeded_scenario_and_records_configuration() -> None:
    audit = audit_scenario(
        manifest(),
        kernel().run,
        configuration=(("z", "2"), ("a", "1")),
        environment=(("runner", "test"),),
    )
    assert audit.stable is True
    assert audit.configuration == (("a", "1"), ("z", "2"))
    assert audit.environment == (("runner", "test"),)
    assert audit.seed == 7
    assert audit.evidence()["stable"] is True


def test_audit_fails_critical_contract_on_digest_drift() -> None:
    first = kernel().run(manifest())
    calls = 0

    def unstable(value: ScenarioManifest) -> ScenarioRun:
        nonlocal calls
        calls += 1
        result = kernel().run(value)
        return result if calls == 1 else replace(result, replay_digest="f" * 64)

    with pytest.raises(DeterminismViolationError) as raised:
        audit_scenario(manifest(), unstable)
    assert raised.value.audit.stable is False
    assert raised.value.audit.first_digest == first.replay_digest


def test_allowed_nondeterminism_is_recorded_without_passing_as_stable() -> None:
    calls = 0

    def varying(value: ScenarioManifest) -> ScenarioRun:
        nonlocal calls
        calls += 1
        result = kernel().run(value)
        return result if calls == 1 else replace(result, replay_digest="a" * 64)

    contract = DeterminismContract("test-observer", "NONDETERMINISTIC_ALLOWED", "observational")
    audit = audit_scenario(manifest(), varying, contract=contract)
    assert audit.stable is False


def test_reproducibility_audit_evidence_is_json_ready() -> None:
    audit = ReproducibilityAudit(
        DeterminismContract("test", "DETERMINISM_CRITICAL"),
        1,
        (),
        (),
        "a" * 64,
        "a" * 64,
    )
    assert audit.evidence()["first_digest"] == "a" * 64
