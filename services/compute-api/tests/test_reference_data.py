from __future__ import annotations

import hashlib

import pytest

from routemind_compute.application.reference_data import (
    ReferenceDataCatalog,
    ReferenceDataConflictError,
    ReferenceDataError,
    ReferenceDataIdentity,
)
from routemind_compute.application.routebench import BenchmarkManifest
from routemind_compute.application.simulation import CourierState, DemandEvent, ScenarioManifest
from routemind_compute.domain.dispatch import GeoPoint


def identity(version: str = "v1", digest_byte: str = "a") -> ReferenceDataIdentity:
    return ReferenceDataIdentity(
        "travel",
        "deterministic-local",
        version,
        digest_byte * 64,
        "fixture-builder",
    )


def test_identity_is_stable_and_catalog_links_content_and_manifest_digests() -> None:
    catalog = ReferenceDataCatalog((identity(),))

    assert catalog.get("travel:deterministic-local:v1").reference_data_id == (
        "travel:deterministic-local:v1"
    )
    link = catalog.link("travel:deterministic-local:v1")
    assert link["content_digest"] == "a" * 64
    assert len(link["reference_data_digest"]) == 64
    assert catalog.snapshot() == (identity(),)


def test_catalog_rejects_mutation_and_requires_additive_supersession() -> None:
    catalog = ReferenceDataCatalog((identity(),))
    with pytest.raises(ReferenceDataConflictError, match="immutable"):
        catalog.register(identity(digest_byte="b"))

    replacement = ReferenceDataIdentity(
        "travel",
        "deterministic-local",
        "v2",
        hashlib.sha256(b"v2").hexdigest(),
        "fixture-builder",
        supersedes="travel:deterministic-local:v1",
    )
    assert catalog.register(replacement).reference_data_id.endswith(":v2")

    with pytest.raises(ReferenceDataError, match="superseded"):
        ReferenceDataCatalog(
            (
                ReferenceDataIdentity(
                    "zone",
                    "city",
                    "v2",
                    "c" * 64,
                    "fixture-builder",
                    supersedes="zone:city:v1",
                ),
            )
        )


def test_identity_rejects_unsupported_or_unverified_values() -> None:
    with pytest.raises(ReferenceDataError):
        ReferenceDataIdentity("unknown", "data", "v1", "a" * 64, "producer")  # type: ignore[arg-type]
    with pytest.raises(ReferenceDataError):
        ReferenceDataIdentity("travel", "data", "v1", "not-a-digest", "producer")


def test_replay_and_benchmark_manifests_carry_reference_identity() -> None:
    scenario = ScenarioManifest(
        "scenario-1",
        7,
        (DemandEvent("request-1", GeoPoint(31.2, 121.4), 0),),
        (CourierState("courier-1", GeoPoint(31.2, 121.4)),),
        reference_data_id="travel:deterministic-local:v1",
    )
    benchmark = BenchmarkManifest(
        "benchmark-1",
        "code-v1",
        "scenario-1",
        7,
        "fixture",
        "local",
        "dataset:v1",
        ("nearest",),
        reference_data_id="travel:deterministic-local:v1",
    )

    assert scenario.reference_data_id == benchmark.reference_data_id
    assert benchmark.canonical_payload()["reference_data_id"] == "travel:deterministic-local:v1"
