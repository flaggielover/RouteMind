from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from routemind_compute.application.statistical_routebench_protocol import (
    StatisticalRouteBenchProtocol,
    load_statistical_routebench_protocol,
)
from routemind_compute.application.statistical_routebench_randomness import (
    CommonRandomNumberError,
    CommonRandomNumberPlan,
    PairedRandomnessManifest,
    PairIdentity,
    RandomStreamPlan,
    StreamRealization,
    build_common_random_number_plan,
    derive_stream_seed,
    freeze_pair_randomness,
)

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = (
    ROOT
    / "docs"
    / "research"
    / "r3"
    / "manifests"
    / "statistical-routebench"
    / "statistical-routebench-v1.json"
)
STREAMS = ("demand", "merchant", "courier", "traffic")


@pytest.fixture(scope="module")
def protocol() -> StatisticalRouteBenchProtocol:
    return load_statistical_routebench_protocol(PROTOCOL_PATH)


def payloads(marker: str = "v1") -> dict[str, object]:
    return {
        "demand": {"arrivals": [{"request_id": "r-1", "tick": 1}], "marker": marker},
        "merchant": {"delays": [0, 2, 1], "marker": marker},
        "courier": {"couriers": [{"courier_id": "c-1"}], "marker": marker},
        "traffic": {"multipliers": [1.0, 1.25], "marker": marker},
    }


def test_frozen_seed_derivation_and_owners_are_exact(
    protocol: StatisticalRouteBenchProtocol,
) -> None:
    plan = build_common_random_number_plan(protocol, "pilot", "normal", 0)

    assert tuple(item.stream_name for item in plan.streams) == STREAMS
    assert tuple(item.owner for item in plan.streams) == (
        "r3b.scenario.demand-arrivals",
        "r3b.scenario.merchant-preparation",
        "r3b.scenario.courier-state",
        "r3b.scenario.travel-conditions",
    )
    assert tuple(item.seed for item in plan.streams) == (
        4816923383674551721,
        1496333979318861507,
        9107451314426469478,
        8847950333973352481,
    )
    assert len({item.seed for item in plan.streams}) == 4
    assert all(len(item.stream_digest) == 64 for item in plan.streams)
    assert plan.pairing_disposition == "VARIANCE_CONTROL_NOT_OBSERVATION_INDEPENDENCE"


def test_repeated_pair_plans_and_realizations_are_digest_stable(
    protocol: StatisticalRouteBenchProtocol,
) -> None:
    first_plan = build_common_random_number_plan(protocol, "pilot", "surge", 3)
    second_plan = build_common_random_number_plan(protocol, "pilot", "surge", 3)
    first = freeze_pair_randomness(first_plan, payloads())
    second = freeze_pair_randomness(second_plan, dict(reversed(tuple(payloads().items()))))

    assert first_plan == second_plan
    assert first_plan.plan_digest == second_plan.plan_digest
    assert first == second
    assert first.manifest_digest == second.manifest_digest
    assert [item.realization_digest for item in first.realizations] == [
        item.realization_digest for item in second.realizations
    ]


@pytest.mark.parametrize(
    ("phase", "regime", "replicate"),
    (
        ("pilot", "normal", 1),
        ("pilot", "surge", 0),
        ("confirmatory", "normal", 1000),
        ("confirmatory", "normal", 1001),
    ),
)
def test_pair_boundaries_produce_distinct_stream_and_plan_digests(
    protocol: StatisticalRouteBenchProtocol, phase: str, regime: str, replicate: int
) -> None:
    baseline = build_common_random_number_plan(protocol, "pilot", "normal", 0)
    other = build_common_random_number_plan(protocol, phase, regime, replicate)

    assert baseline.plan_digest != other.plan_digest
    assert {item.stream_digest for item in baseline.streams}.isdisjoint(
        item.stream_digest for item in other.streams
    )


@pytest.mark.parametrize(
    ("phase", "regime", "replicate", "message"),
    (
        ("exploratory", "normal", 0, "phase"),
        ("pilot", "unknown", 0, "regime"),
        ("pilot", "normal", 8, "pilot replicate"),
        ("confirmatory", "normal", 999, "confirmatory replicate"),
        ("confirmatory", "normal", 1200, "confirmatory replicate"),
        ("pilot", "normal", -1, "non-negative"),
        ("pilot", "normal", True, "integer"),
    ),
)
def test_pair_plan_rejects_out_of_scope_identity(
    protocol: StatisticalRouteBenchProtocol,
    phase: str,
    regime: str,
    replicate: int,
    message: str,
) -> None:
    with pytest.raises(CommonRandomNumberError, match=message):
        build_common_random_number_plan(protocol, phase, regime, replicate)


def test_plan_rejects_protocol_stream_drift(protocol: StatisticalRouteBenchProtocol) -> None:
    drifted = replace(protocol, common_streams=("demand",))
    with pytest.raises(CommonRandomNumberError, match="order drifted"):
        build_common_random_number_plan(drifted, "pilot", "normal", 0)


def test_realizations_are_generated_once_and_both_arms_bind_the_same_digests(
    protocol: StatisticalRouteBenchProtocol,
) -> None:
    even = freeze_pair_randomness(
        build_common_random_number_plan(protocol, "pilot", "normal", 0), payloads()
    )
    candidate, comparator = even.arm_bindings("risk-aware", "weighted-greedy")

    assert (candidate.arm_role, comparator.arm_role) == ("candidate", "comparator")
    assert candidate.pair_manifest_digest == comparator.pair_manifest_digest
    assert candidate.stream_realization_digests == comparator.stream_realization_digests
    assert len(candidate.stream_realization_digests) == 4

    odd = freeze_pair_randomness(
        build_common_random_number_plan(protocol, "pilot", "normal", 1), payloads()
    )
    first, second = odd.arm_bindings("risk-aware", "weighted-greedy")
    assert (first.arm_role, second.arm_role) == ("comparator", "candidate")


def test_realization_content_changes_without_reassigning_stream_ownership(
    protocol: StatisticalRouteBenchProtocol,
) -> None:
    plan = build_common_random_number_plan(protocol, "pilot", "normal", 0)
    first = freeze_pair_randomness(plan, payloads("first"))
    second = freeze_pair_randomness(plan, payloads("second"))

    assert first.plan == second.plan
    assert first.manifest_digest != second.manifest_digest
    assert tuple(item.stream_digest for item in first.realizations) == tuple(
        item.stream_digest for item in second.realizations
    )
    assert all(
        left.content_digest != right.content_digest
        for left, right in zip(first.realizations, second.realizations, strict=True)
    )


def test_realization_rejects_missing_extra_and_noncanonical_payloads(
    protocol: StatisticalRouteBenchProtocol,
) -> None:
    plan = build_common_random_number_plan(protocol, "pilot", "normal", 0)
    missing = payloads()
    del missing["traffic"]
    with pytest.raises(CommonRandomNumberError, match="every frozen stream"):
        freeze_pair_randomness(plan, missing)
    extra = payloads()
    extra["strategy"] = {"arm": "candidate"}
    with pytest.raises(CommonRandomNumberError, match="every frozen stream"):
        freeze_pair_randomness(plan, extra)
    invalid = payloads()
    invalid["traffic"] = {"value": float("nan")}
    with pytest.raises(CommonRandomNumberError, match="not canonical JSON"):
        freeze_pair_randomness(plan, invalid)


@pytest.mark.parametrize(("candidate", "comparator"), (("", "baseline"), ("same", "same")))
def test_arm_binding_rejects_invalid_strategy_identity(
    protocol: StatisticalRouteBenchProtocol, candidate: str, comparator: str
) -> None:
    manifest = freeze_pair_randomness(
        build_common_random_number_plan(protocol, "pilot", "normal", 0), payloads()
    )
    with pytest.raises(CommonRandomNumberError, match="strateg"):
        manifest.arm_bindings(candidate, comparator)


def test_public_invariants_fail_closed(protocol: StatisticalRouteBenchProtocol) -> None:
    pair = PairIdentity(protocol.protocol_id, "pilot", "normal", 0)
    stream = build_common_random_number_plan(protocol, "pilot", "normal", 0).streams[0]
    with pytest.raises(CommonRandomNumberError, match="owner"):
        RandomStreamPlan(pair, "demand", "other", stream.seed, stream.stream_digest)
    with pytest.raises(CommonRandomNumberError, match="63-bit"):
        RandomStreamPlan(pair, "demand", stream.owner, 1 << 63, stream.stream_digest)
    with pytest.raises(CommonRandomNumberError, match="SHA-256"):
        RandomStreamPlan(pair, "demand", stream.owner, stream.seed, "BAD")
    with pytest.raises(CommonRandomNumberError, match="frozen order"):
        CommonRandomNumberPlan(pair, tuple(reversed((stream,))))
    with pytest.raises(KeyError, match="unknown common random stream"):
        build_common_random_number_plan(protocol, "pilot", "normal", 0).stream("unknown")
    with pytest.raises(CommonRandomNumberError, match="name is not frozen"):
        derive_stream_seed(pair, "strategy")


def test_realization_and_manifest_reject_plan_mismatch(
    protocol: StatisticalRouteBenchProtocol,
) -> None:
    plan = build_common_random_number_plan(protocol, "pilot", "normal", 0)
    manifest = freeze_pair_randomness(plan, payloads())
    first = manifest.realizations[0]
    with pytest.raises(CommonRandomNumberError, match="owner"):
        StreamRealization(first.stream_name, "other", first.stream_digest, first.content_digest)
    with pytest.raises(CommonRandomNumberError, match="SHA-256"):
        StreamRealization(first.stream_name, first.owner, "BAD", first.content_digest)
    drifted = replace(first, stream_digest="f" * 64)
    with pytest.raises(CommonRandomNumberError, match="does not match"):
        PairedRandomnessManifest(plan, (drifted, *manifest.realizations[1:]))
