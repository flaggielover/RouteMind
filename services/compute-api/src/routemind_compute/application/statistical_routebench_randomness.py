"""Content-addressed common-random-number ownership for Statistical RouteBench."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.statistical_routebench_protocol import (
    StatisticalRouteBenchProtocol,
)

_STREAM_ORDER = ("demand", "merchant", "courier", "traffic")
_OWNER_BY_STREAM = {
    "demand": "r3b.scenario.demand-arrivals",
    "merchant": "r3b.scenario.merchant-preparation",
    "courier": "r3b.scenario.courier-state",
    "traffic": "r3b.scenario.travel-conditions",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MAX_SEED = (1 << 63) - 1
_PAIRING_DISPOSITION = "VARIANCE_CONTROL_NOT_OBSERVATION_INDEPENDENCE"


class CommonRandomNumberError(ValueError):
    """Raised when an R3-B random-stream ownership invariant is violated."""


@dataclass(frozen=True, slots=True)
class PairIdentity:
    protocol_id: str
    phase: str
    regime_id: str
    replicate: int

    def __post_init__(self) -> None:
        if not self.protocol_id.strip() or not self.regime_id.strip():
            raise CommonRandomNumberError("pair identity must not be blank")
        if self.phase not in {"pilot", "confirmatory"}:
            raise CommonRandomNumberError("pair phase must be pilot or confirmatory")
        if not isinstance(self.replicate, int) or isinstance(self.replicate, bool):
            raise CommonRandomNumberError("pair replicate must be an integer")
        if self.replicate < 0:
            raise CommonRandomNumberError("pair replicate must be non-negative")

    def payload(self) -> dict[str, object]:
        return {
            "protocol_id": self.protocol_id,
            "phase": self.phase,
            "regime_id": self.regime_id,
            "replicate": self.replicate,
        }


@dataclass(frozen=True, slots=True)
class RandomStreamPlan:
    pair: PairIdentity
    stream_name: str
    owner: str
    seed: int
    stream_digest: str

    def __post_init__(self) -> None:
        expected_owner = _OWNER_BY_STREAM.get(self.stream_name)
        if expected_owner is None or self.owner != expected_owner:
            raise CommonRandomNumberError("random stream owner is invalid")
        if not isinstance(self.seed, int) or isinstance(self.seed, bool):
            raise CommonRandomNumberError("random stream seed must be an integer")
        if not 0 <= self.seed <= _MAX_SEED:
            raise CommonRandomNumberError("random stream seed exceeds the 63-bit boundary")
        if not _SHA256.fullmatch(self.stream_digest):
            raise CommonRandomNumberError("random stream digest must be lowercase SHA-256")

    def payload(self) -> dict[str, object]:
        return {
            **self.pair.payload(),
            "stream_name": self.stream_name,
            "owner": self.owner,
            "seed": self.seed,
            "derivation": (
                "SHA256(protocol_id|phase|regime_id|replicate|stream_name), "
                "first 16 hex digits masked to 63 bits"
            ),
        }


@dataclass(frozen=True, slots=True)
class CommonRandomNumberPlan:
    pair: PairIdentity
    streams: tuple[RandomStreamPlan, ...]

    def __post_init__(self) -> None:
        if tuple(item.stream_name for item in self.streams) != _STREAM_ORDER:
            raise CommonRandomNumberError("random streams must use the frozen order")
        if any(item.pair != self.pair for item in self.streams):
            raise CommonRandomNumberError("random stream escaped its pair identity")

    @property
    def plan_digest(self) -> str:
        return canonical_digest(self.payload())

    @property
    def pairing_disposition(self) -> str:
        return _PAIRING_DISPOSITION

    def payload(self) -> dict[str, object]:
        return {
            "pair": self.pair.payload(),
            "streams": [
                {**item.payload(), "stream_digest": item.stream_digest} for item in self.streams
            ],
            "pairing_disposition": _PAIRING_DISPOSITION,
        }

    def stream(self, stream_name: str) -> RandomStreamPlan:
        for item in self.streams:
            if item.stream_name == stream_name:
                return item
        raise KeyError(f"unknown common random stream: {stream_name}")


@dataclass(frozen=True, slots=True)
class StreamRealization:
    stream_name: str
    owner: str
    stream_digest: str
    content_digest: str

    def __post_init__(self) -> None:
        if _OWNER_BY_STREAM.get(self.stream_name) != self.owner:
            raise CommonRandomNumberError("stream realization owner is invalid")
        if not _SHA256.fullmatch(self.stream_digest) or not _SHA256.fullmatch(self.content_digest):
            raise CommonRandomNumberError("stream realization digests must be lowercase SHA-256")

    @property
    def realization_digest(self) -> str:
        return canonical_digest(self.payload())

    def payload(self) -> dict[str, str]:
        return {
            "stream_name": self.stream_name,
            "owner": self.owner,
            "stream_digest": self.stream_digest,
            "content_digest": self.content_digest,
        }


@dataclass(frozen=True, slots=True)
class ArmRandomnessBinding:
    arm_role: str
    strategy: str
    pair_manifest_digest: str
    stream_realization_digests: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class PairedRandomnessManifest:
    plan: CommonRandomNumberPlan
    realizations: tuple[StreamRealization, ...]

    def __post_init__(self) -> None:
        if tuple(item.stream_name for item in self.realizations) != _STREAM_ORDER:
            raise CommonRandomNumberError("stream realizations must use the frozen order")
        planned = {item.stream_name: item for item in self.plan.streams}
        if any(
            item.owner != planned[item.stream_name].owner
            or item.stream_digest != planned[item.stream_name].stream_digest
            for item in self.realizations
        ):
            raise CommonRandomNumberError("stream realization does not match its frozen plan")

    @property
    def manifest_digest(self) -> str:
        return canonical_digest(self.payload())

    def payload(self) -> dict[str, object]:
        return {
            "plan_digest": self.plan.plan_digest,
            "pair": self.plan.pair.payload(),
            "realizations": [
                {**item.payload(), "realization_digest": item.realization_digest}
                for item in self.realizations
            ],
            "shared_across_arms": True,
            "pairing_disposition": _PAIRING_DISPOSITION,
        }

    def arm_bindings(
        self, candidate_strategy: str, comparator_strategy: str
    ) -> tuple[ArmRandomnessBinding, ArmRandomnessBinding]:
        if not candidate_strategy.strip() or not comparator_strategy.strip():
            raise CommonRandomNumberError("bound strategy identities must not be blank")
        if candidate_strategy == comparator_strategy:
            raise CommonRandomNumberError("paired arms must use distinct strategies")
        shared = tuple((item.stream_name, item.realization_digest) for item in self.realizations)
        candidate = ArmRandomnessBinding(
            "candidate", candidate_strategy, self.manifest_digest, shared
        )
        comparator = ArmRandomnessBinding(
            "comparator", comparator_strategy, self.manifest_digest, shared
        )
        if self.plan.pair.replicate % 2 == 0:
            return candidate, comparator
        return comparator, candidate


def derive_stream_seed(pair: PairIdentity, stream_name: str) -> int:
    if stream_name not in _OWNER_BY_STREAM:
        raise CommonRandomNumberError("random stream name is not frozen")
    material = f"{pair.protocol_id}|{pair.phase}|{pair.regime_id}|{pair.replicate}|{stream_name}"
    return int(sha256(material.encode("utf-8")).hexdigest()[:16], 16) & _MAX_SEED


def build_common_random_number_plan(
    protocol: StatisticalRouteBenchProtocol,
    phase: str,
    regime_id: str,
    replicate: int,
) -> CommonRandomNumberPlan:
    pair = PairIdentity(protocol.protocol_id, phase, regime_id, replicate)
    if regime_id not in protocol.regime_ids:
        raise CommonRandomNumberError("pair regime is not frozen by the protocol")
    if tuple(protocol.common_streams) != _STREAM_ORDER:
        raise CommonRandomNumberError("protocol common-stream order drifted")
    if phase == "pilot" and replicate >= protocol.pilot_replicates_per_regime:
        raise CommonRandomNumberError("pilot replicate is outside the frozen range")
    if phase == "confirmatory" and not (
        protocol.confirmatory_replicate_start
        <= replicate
        < protocol.confirmatory_replicate_start + protocol.maximum_confirmatory_pairs_per_regime
    ):
        raise CommonRandomNumberError("confirmatory replicate is outside the frozen range")
    streams = tuple(_stream_plan(pair, stream_name) for stream_name in _STREAM_ORDER)
    return CommonRandomNumberPlan(pair, streams)


def freeze_pair_randomness(
    plan: CommonRandomNumberPlan, payloads: Mapping[str, object]
) -> PairedRandomnessManifest:
    if set(payloads) != set(_STREAM_ORDER):
        raise CommonRandomNumberError("realized payloads must cover every frozen stream exactly")
    realizations: list[StreamRealization] = []
    for stream_name in _STREAM_ORDER:
        stream = plan.stream(stream_name)
        try:
            content_digest = canonical_digest(payloads[stream_name])
        except (TypeError, ValueError) as error:
            raise CommonRandomNumberError(
                f"{stream_name} realization is not canonical JSON"
            ) from error
        realizations.append(
            StreamRealization(stream_name, stream.owner, stream.stream_digest, content_digest)
        )
    return PairedRandomnessManifest(plan, tuple(realizations))


def _stream_plan(pair: PairIdentity, stream_name: str) -> RandomStreamPlan:
    seed = derive_stream_seed(pair, stream_name)
    owner = _OWNER_BY_STREAM[stream_name]
    payload = {
        **pair.payload(),
        "stream_name": stream_name,
        "owner": owner,
        "seed": seed,
        "derivation": (
            "SHA256(protocol_id|phase|regime_id|replicate|stream_name), "
            "first 16 hex digits masked to 63 bits"
        ),
    }
    return RandomStreamPlan(pair, stream_name, owner, seed, canonical_digest(payload))


__all__ = [
    "ArmRandomnessBinding",
    "CommonRandomNumberError",
    "CommonRandomNumberPlan",
    "PairIdentity",
    "PairedRandomnessManifest",
    "RandomStreamPlan",
    "StreamRealization",
    "build_common_random_number_plan",
    "derive_stream_seed",
    "freeze_pair_randomness",
]
