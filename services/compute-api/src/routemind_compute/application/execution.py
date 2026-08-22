from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from routemind_compute.domain.dispatch import DispatchDecision


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, allow_nan=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class ExecutionProvenance:
    input_digest: str
    output_digest: str


def execution_provenance(canonical_input: Any, decision: DispatchDecision) -> ExecutionProvenance:
    canonical_output = {
        "request_id": decision.request_id,
        "strategy": decision.strategy,
        "strategy_version": decision.strategy_version,
        "courier_id": decision.courier_id,
        "score": decision.score,
        "rationale": decision.rationale,
        "metadata": decision.metadata,
    }
    return ExecutionProvenance(
        canonical_digest(canonical_input), canonical_digest(canonical_output)
    )
