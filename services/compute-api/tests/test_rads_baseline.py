from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.rads import (
    RadsObjective,
    RadsSelector,
    RadsStateEncoder,
    RiskSignal,
)
from routemind_compute.application.rads_baseline import (
    RadsBaselineError,
    load_rads_baseline_plan,
)
from routemind_compute.domain.dispatch import CourierCandidate, DispatchProblem, GeoPoint

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "docs" / "research" / "r3" / "manifests" / "rads" / "rads-baseline-v1.json"


def _payload() -> dict[str, object]:
    parsed: object = json.loads(PLAN.read_text(encoding="utf-8"))
    if not isinstance(parsed, Mapping):
        raise AssertionError("fixture must be an object")
    return cast(dict[str, object], parsed)


def _mapping(value: object) -> dict[str, object]:
    return dict(cast(Mapping[str, object], value))


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    unsigned = dict(payload)
    unsigned["baseline_digest"] = canonical_digest(
        {key: value for key, value in unsigned.items() if key != "baseline_digest"}
    )
    path = tmp_path / "rads-baseline.json"
    path.write_text(json.dumps(unsigned, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_plan_freezes_rads_contract_and_matches_selector() -> None:
    plan = load_rads_baseline_plan(PLAN)
    assert plan.baseline_id == "RADS-BASELINE-v1"
    assert (
        plan.baseline_digest == "a907a0a722e8782aa76277637fa92205cc10046e5aca85b2de81e555623016c3"
    )
    assert plan.manifest_sha256 == sha256(PLAN.read_bytes()).hexdigest()
    strategies = _mapping(plan.payload["strategies"])
    assert strategies["baseline_order"] == ["nearest", "weighted-greedy"]
    assert strategies["variants"] == ["full"]
    objective = _mapping(plan.payload["objective"])
    assert objective["distance_weight"] == 1.0
    assert objective["risk_weight"] == 1.0
    assert objective["risk_multiplier"] == 1.0

    problem = DispatchProblem(
        "r3-340-fixture",
        GeoPoint(31.2304, 121.4737),
        (
            CourierCandidate("near-risky", GeoPoint(31.2305, 121.4738)),
            CourierCandidate("far-safe", GeoPoint(31.2350, 121.4780)),
        ),
    )
    risks = (
        RiskSignal("near-risky", 0.8, 20.0),
        RiskSignal("far-safe", 0.01, 5.0),
    )
    state = RadsStateEncoder().encode(problem, risks, risk_multiplier=1.0)
    first = RadsSelector(RadsObjective(1.0, 1.0)).select(state, variant="full")
    second = RadsSelector(RadsObjective(1.0, 1.0)).select(state, variant="full")
    assert first == second
    assert first.courier_id == "far-safe"
    assert first.state_digest == state.digest


def test_plan_rejects_json_digest_identity_and_shape(tmp_path: Path) -> None:
    payload = _payload()
    payload["baseline_id"] = "changed"
    forged = tmp_path / "forged.json"
    forged.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RadsBaselineError, match="digest"):
        load_rads_baseline_plan(forged)

    scalar = tmp_path / "scalar.json"
    scalar.write_text("[]", encoding="utf-8")
    with pytest.raises(RadsBaselineError, match="JSON object"):
        load_rads_baseline_plan(scalar)

    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b"not-json")
    with pytest.raises(RadsBaselineError, match="UTF-8 JSON"):
        load_rads_baseline_plan(invalid)

    payload = _payload()
    del payload["scope"]
    with pytest.raises(RadsBaselineError, match="fields mismatch"):
        load_rads_baseline_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["task_id"] = "R3-339"
    with pytest.raises(RadsBaselineError, match="identity"):
        load_rads_baseline_plan(_write(tmp_path, payload))


def test_plan_rejects_policy_and_lineage_drift(tmp_path: Path) -> None:
    payload = _payload()
    scope = _mapping(payload["scope"])
    scope["durable_truth"] = "POSTGRESQL"
    payload["scope"] = scope
    with pytest.raises(RadsBaselineError, match="durable truth"):
        load_rads_baseline_plan(_write(tmp_path, payload))

    payload = _payload()
    state = _mapping(payload["state"])
    state["fields"] = ["candidates"]
    payload["state"] = state
    with pytest.raises(RadsBaselineError, match="state field"):
        load_rads_baseline_plan(_write(tmp_path, payload))

    payload = _payload()
    selector = _mapping(payload["selector"])
    selector["rank_key"] = ["courier_id"]
    payload["selector"] = selector
    with pytest.raises(RadsBaselineError, match="rank key"):
        load_rads_baseline_plan(_write(tmp_path, payload))

    payload = _payload()
    fallbacks = _mapping(payload["fallbacks"])
    fallbacks["silent_substitution"] = True
    payload["fallbacks"] = fallbacks
    with pytest.raises(RadsBaselineError, match="silently substitute"):
        load_rads_baseline_plan(_write(tmp_path, payload))

    payload = _payload()
    determinism = _mapping(payload["determinism"])
    determinism["wall_clock_in_digest"] = True
    payload["determinism"] = determinism
    with pytest.raises(RadsBaselineError, match="wall-clock"):
        load_rads_baseline_plan(_write(tmp_path, payload))

    payload = _payload()
    sources = list(cast(list[object], payload["source_artifacts"]))
    first = _mapping(sources[0])
    first["sha256"] = "invalid"
    sources[0] = first
    payload["source_artifacts"] = sources
    with pytest.raises(RadsBaselineError, match="SHA-256"):
        load_rads_baseline_plan(_write(tmp_path, payload))


def test_plan_rejects_nested_types_and_numeric_policy(tmp_path: Path) -> None:
    payload = _payload()
    objective = _mapping(payload["objective"])
    objective["distance_weight"] = 2.0
    payload["objective"] = objective
    with pytest.raises(RadsBaselineError, match="objective weights"):
        load_rads_baseline_plan(_write(tmp_path, payload))

    payload = _payload()
    risk = _mapping(payload["risk"])
    risk["failure_probability"] = "invalid"
    payload["risk"] = risk
    with pytest.raises(RadsBaselineError, match="object"):
        load_rads_baseline_plan(_write(tmp_path, payload))

    payload = _payload()
    thresholds = _mapping(payload["thresholds"])
    thresholds["max_text_length"] = True
    payload["thresholds"] = thresholds
    with pytest.raises(RadsBaselineError, match="integer"):
        load_rads_baseline_plan(_write(tmp_path, payload))

    payload = _payload()
    limitations = list(cast(list[object], payload["limitations"]))
    limitations[0] = ""
    payload["limitations"] = limitations
    with pytest.raises(RadsBaselineError, match="limitations"):
        load_rads_baseline_plan(_write(tmp_path, payload))


def test_plan_rejects_remaining_fail_closed_paths(tmp_path: Path) -> None:
    def reject(mutate: Callable[[dict[str, object]], None], match: str) -> None:
        payload = _payload()
        mutate(payload)
        with pytest.raises(RadsBaselineError, match=match):
            load_rads_baseline_plan(_write(tmp_path, payload))

    reject(lambda payload: payload.update(claim_boundary="other"), "claim boundary")
    reject(
        lambda payload: payload.update(
            scope={**_mapping(payload["scope"]), "hard_realtime": "AUTHORIZED"}
        ),
        "hard real-time",
    )
    reject(
        lambda payload: payload.update(
            state={**_mapping(payload["state"]), "candidate_fields": ["courier_id"]}
        ),
        "candidate field",
    )
    reject(
        lambda payload: payload.update(state={**_mapping(payload["state"]), "digest": "other"}),
        "state digest",
    )

    for key, match in (
        ("control", "control strategy identity"),
        ("comparator", "comparator strategy identity"),
    ):

        def mutate_strategy(payload: dict[str, object], strategy_key: str = key) -> None:
            strategies = _mapping(payload["strategies"])
            payload["strategies"] = {
                **strategies,
                strategy_key: {
                    **_mapping(strategies[strategy_key]),
                    "version": "2.0.0",
                },
            }

        reject(mutate_strategy, match)
    reject(
        lambda payload: payload.update(
            strategies={
                **_mapping(payload["strategies"]),
                "control": {
                    **_mapping(_mapping(payload["strategies"])["control"]),
                    "maturity": "RESEARCH",
                },
            }
        ),
        "control strategy maturity",
    )
    reject(
        lambda payload: payload.update(
            strategies={
                **_mapping(payload["strategies"]),
                "rads": {**_mapping(_mapping(payload["strategies"])["rads"]), "name": "other"},
            }
        ),
        "RADS strategy identity",
    )
    reject(
        lambda payload: payload.update(
            strategies={
                **_mapping(payload["strategies"]),
                "rads": {
                    **_mapping(_mapping(payload["strategies"])["rads"]),
                    "maturity": "BASELINE",
                },
            }
        ),
        "RADS strategy maturity",
    )
    reject(
        lambda payload: payload.update(
            strategies={**_mapping(payload["strategies"]), "baseline_order": ["weighted-greedy"]}
        ),
        "baseline order",
    )
    reject(
        lambda payload: payload.update(
            strategies={**_mapping(payload["strategies"]), "variants": ["risk-only"]}
        ),
        "variants",
    )

    reject(
        lambda payload: payload.update(
            objective={**_mapping(payload["objective"]), "formula": "other"}
        ),
        "objective formula",
    )
    reject(
        lambda payload: payload.update(
            objective={**_mapping(payload["objective"]), "units": "other"}
        ),
        "objective identity",
    )
    reject(
        lambda payload: payload.update(
            objective={**_mapping(payload["objective"]), "risk_multiplier": 2.0}
        ),
        "risk multiplier",
    )
    reject(
        lambda payload: payload.update(
            risk={**_mapping(payload["risk"]), "signal_fields": ["impact_minutes"]}
        ),
        "risk fields",
    )
    reject(
        lambda payload: payload.update(
            risk={
                **_mapping(payload["risk"]),
                "failure_probability": {"inclusive": True, "maximum": 2.0, "minimum": 0.0},
            }
        ),
        "probability bounds",
    )
    reject(
        lambda payload: payload.update(
            risk={
                **_mapping(payload["risk"]),
                "impact_minutes": {"inclusive": False, "minimum": 0.0},
            }
        ),
        "impact bounds",
    )
    reject(
        lambda payload: payload.update(
            selector={**_mapping(payload["selector"]), "tie_break": "other"}
        ),
        "selector policy",
    )
    reject(
        lambda payload: payload.update(
            thresholds={**_mapping(payload["thresholds"]), "max_metadata_items": 31}
        ),
        "input thresholds",
    )
    reject(
        lambda payload: payload.update(
            thresholds={**_mapping(payload["thresholds"]), "risk_profile": "other"}
        ),
        "risk thresholds",
    )
    reject(
        lambda payload: payload.update(
            weights={
                **_mapping(payload["weights"]),
                "rads_objective": {"distance": 2.0, "risk": 1.0},
            }
        ),
        "objective weight vector",
    )
    reject(
        lambda payload: payload.update(
            weights={
                **_mapping(payload["weights"]),
                "risk_aware_strategy": {"distance": 1.0},
            }
        ),
        "risk_aware_strategy fields mismatch",
    )
    reject(
        lambda payload: payload.update(
            weights={
                **_mapping(payload["weights"]),
                "risk_aware_strategy": {
                    **_mapping(_mapping(payload["weights"])["risk_aware_strategy"]),
                    "balance": 1.0,
                },
            }
        ),
        "risk-aware strategy weight vector",
    )
    reject(
        lambda payload: payload.update(
            fallbacks={**_mapping(payload["fallbacks"]), "invalid_input": "fallback"}
        ),
        "fallback policy",
    )
    reject(
        lambda payload: payload.update(
            determinism={**_mapping(payload["determinism"]), "canonical_json": "other"}
        ),
        "canonicalization",
    )
    reject(
        lambda payload: payload.update(
            determinism={
                **_mapping(payload["determinism"]),
                "ordering": ["other"],
            }
        ),
        "ordering policy",
    )
    reject(
        lambda payload: payload.__setitem__("limitations", []),
        "limitations",
    )

    def incomplete_sources(payload: dict[str, object]) -> None:
        payload["source_artifacts"] = cast(list[object], payload["source_artifacts"])[:-1]

    reject(incomplete_sources, "source artifact list")

    reject(
        lambda payload: payload.__setitem__("source_artifacts", "invalid"),
        "source_artifacts must be an array",
    )

    def unknown_source(payload: dict[str, object]) -> None:
        sources = list(cast(list[object], payload["source_artifacts"]))
        source = _mapping(sources[0])
        source["path"] = "other.py"
        sources[0] = source
        payload["source_artifacts"] = sources

    reject(unknown_source, "source artifact identity")

    def reversed_sources(payload: dict[str, object]) -> None:
        payload["source_artifacts"] = list(
            reversed(cast(list[object], payload["source_artifacts"]))
        )

    reject(reversed_sources, "frozen order")

    reject(
        lambda payload: payload.update(
            thresholds={**_mapping(payload["thresholds"]), "risk_multiplier": []}
        ),
        "non-empty text",
    )
    reject(
        lambda payload: payload.update(
            state={**_mapping(payload["state"]), "fields": [None, "risk_multiplier", "candidates"]}
        ),
        "state field must be non-empty text",
    )
    reject(
        lambda payload: payload.update(
            objective={**_mapping(payload["objective"]), "distance_weight": "invalid"}
        ),
        "finite number",
    )
    reject(
        lambda payload: payload.update(
            fallbacks={**_mapping(payload["fallbacks"]), "silent_substitution": "false"}
        ),
        "boolean",
    )


def test_plan_file_digest_is_stable() -> None:
    first = load_rads_baseline_plan(PLAN)
    second = load_rads_baseline_plan(PLAN)
    assert first.manifest_sha256 == second.manifest_sha256
    assert first.baseline_digest == second.baseline_digest
