"""Fail-closed R3-346 interpretable policy-boundary support audit."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Literal

from routemind_compute.application.execution import canonical_digest

_SCHEMA = "routemind-policy-boundaries-v1"
_CLAIM_BOUNDARY = (
    "INTERPRETABLE_POLICY_BOUNDARY_REQUIRES_EMPIRICAL_SUPPORT_UNCERTAINTY_AND_SENSITIVITY"
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_AXES = (
    "relative_advantage",
    "dwell_ticks",
    "pressure_ticks",
    "regime_id",
    "strategy_pair",
    "risk_score",
    "feasibility_margin",
)
_AXIS_ROLES = (
    "continuous_state",
    "duration_state",
    "duration_state",
    "categorical_context",
    "categorical_decision",
    "continuous_constraint",
    "continuous_constraint",
)
_OUTPUTS = (
    "decision_regions",
    "boundary_rules",
    "support_counts",
    "uncertainty_intervals",
    "sensitivity_results",
)
_SUPPORT = (
    "empirical_stability_cells",
    "selected_strategy_labels",
    "alternate_strategy_outcomes",
    "risk_outcomes",
    "feasibility_outcomes",
    "pairing_unit",
    "regime_identity",
)
_SOURCE_DIGESTS = {
    "stability_map_plan": "c6d7d4a5ac088570731e80a189c12cd79792256ac3669bdeed5f9049d6b4ee14",
    "safe_rads_experiment": "182a3e6217f2c8e918049a4d55b78e340c8882a58e5dad106a7f738c3433783c",
    "decision_corpus_manifest": "d92c58cbf196e3f9ab7a157e575831f4c35a9508d3482a6f6ba90728c89e569b",
    "decision_corpus_records": "a9fbc9d01cf8bddff917e3b067342b091877bc24cbabbf9e776cc8e74e06799f",
}
_MINIMUM_CLASSES = 2
_MINIMUM_PER_STRATEGY = 30
_MINIMUM_STABILITY_CELLS = 2


class PolicyBoundaryError(ValueError):
    """Raised when the boundary plan or support input violates the contract."""


@dataclass(frozen=True, slots=True)
class PolicyBoundaryPlan:
    payload: Mapping[str, object]
    plan_digest: str
    manifest_sha256: str

    @property
    def study_id(self) -> str:
        return _text(self.payload, "study_id")


@dataclass(frozen=True, slots=True)
class PolicyBoundaryAudit:
    status: Literal["INSUFFICIENT_DATA", "READY_FOR_INTERPRETABLE_LEARNING"]
    plan_digest: str
    available_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]
    strategy_counts: tuple[tuple[str, int], ...]
    eligible_stability_cells: int
    axis_status: tuple[tuple[str, str], ...]
    output_status: tuple[tuple[str, str], ...]
    uncertainty_status: str
    sensitivity_status: str
    reason: str
    claim_boundary: str = _CLAIM_BOUNDARY


def load_policy_boundary_plan(path: Path | str) -> PolicyBoundaryPlan:
    plan_path = Path(path).expanduser().resolve()
    try:
        raw = plan_path.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PolicyBoundaryError("policy-boundary plan is not valid UTF-8 JSON") from exc
    if not isinstance(parsed, Mapping):
        raise PolicyBoundaryError("policy-boundary plan must be a JSON object")
    payload = dict(parsed)
    digest = _text(payload, "plan_digest")
    unsigned = dict(payload)
    del unsigned["plan_digest"]
    if canonical_digest(unsigned) != digest:
        raise PolicyBoundaryError("policy-boundary plan digest does not match content")
    _validate(payload)
    return PolicyBoundaryPlan(payload, digest, sha256(raw).hexdigest())


def audit_policy_boundary_support(
    plan: PolicyBoundaryPlan,
    artifact_support: Mapping[str, bool],
    strategy_counts: Mapping[str, int],
    eligible_stability_cells: int,
) -> PolicyBoundaryAudit:
    if set(artifact_support) != set(_SUPPORT):
        raise PolicyBoundaryError("policy-boundary support fields mismatch")
    if (
        isinstance(eligible_stability_cells, bool)
        or not isinstance(eligible_stability_cells, int)
        or eligible_stability_cells < 0
    ):
        raise PolicyBoundaryError("eligible stability cells must be a non-negative integer")
    if any(
        not isinstance(strategy, str)
        or not strategy.strip()
        or isinstance(count, bool)
        or not isinstance(count, int)
        or count < 0
        for strategy, count in strategy_counts.items()
    ):
        raise PolicyBoundaryError("strategy counts must map names to non-negative integers")

    available = tuple(field for field in _SUPPORT if artifact_support[field])
    missing = tuple(field for field in _SUPPORT if not artifact_support[field])
    counts = tuple(sorted(strategy_counts.items()))
    class_support = len(counts) >= _MINIMUM_CLASSES and all(
        count >= _MINIMUM_PER_STRATEGY for _, count in counts
    )
    cell_support = eligible_stability_cells >= _MINIMUM_STABILITY_CELLS
    ready = not missing and class_support and cell_support

    if ready:
        return PolicyBoundaryAudit(
            "READY_FOR_INTERPRETABLE_LEARNING",
            plan.plan_digest,
            available,
            (),
            counts,
            eligible_stability_cells,
            tuple((axis, "READY_FOR_SUPPORTED_BOUNDARY") for axis in _AXES),
            tuple((output, "READY_FOR_PREREGISTERED_ESTIMATION") for output in _OUTPUTS),
            "READY_FOR_PAIRED_BOOTSTRAP_INTERVALS",
            "READY_FOR_PREREGISTERED_SENSITIVITY",
            "complete support meets frozen class, record, and stability-cell thresholds",
        )

    if missing:
        reason = (
            "upstream artifacts lack eligible stability cells, strategy labels, alternate "
            "outcomes, Safe-RADS outcomes, or paired regime identity"
        )
    elif not class_support:
        reason = "strategy classes do not meet the frozen minimum of 30 records per class"
    else:
        reason = "fewer than two eligible empirical stability cells are available"
    return PolicyBoundaryAudit(
        "INSUFFICIENT_DATA",
        plan.plan_digest,
        available,
        missing,
        counts,
        eligible_stability_cells,
        tuple((axis, "NOT_MAPPED_INSUFFICIENT_EMPIRICAL_SUPPORT") for axis in _AXES),
        tuple((output, "NOT_ESTIMATED_INSUFFICIENT_BOUNDARY_SUPPORT") for output in _OUTPUTS),
        "NOT_ESTIMATED_NO_SUPPORTED_BOUNDARY",
        "NOT_RUN_NO_SUPPORTED_BOUNDARY",
        reason,
    )


def _validate(value: Mapping[str, object]) -> None:
    required = {
        "schema_version",
        "task_id",
        "study_id",
        "frozen_at_utc",
        "question",
        "boundary_axes",
        "required_outputs",
        "learning_policy",
        "coverage_policy",
        "uncertainty_policy",
        "sensitivity_policy",
        "support_requirements",
        "source_lineage",
        "execution_policy",
        "claim_boundary",
        "plan_digest",
    }
    if set(value) != required:
        raise PolicyBoundaryError("policy-boundary plan fields mismatch")
    if _text(value, "schema_version") != _SCHEMA or _text(value, "task_id") != "R3-346":
        raise PolicyBoundaryError("policy-boundary identity is unsupported")
    if _text(value, "study_id") != "r3-346-interpretable-policy-boundaries-v1":
        raise PolicyBoundaryError("policy-boundary study identifier is not frozen")
    _text(value, "frozen_at_utc")
    _text(value, "question")
    if _text(value, "claim_boundary") != _CLAIM_BOUNDARY:
        raise PolicyBoundaryError("policy-boundary claim boundary is missing")
    _validate_axes(_sequence(value, "boundary_axes"))
    outputs = tuple(
        _text_item(item, "required output") for item in _sequence(value, "required_outputs")
    )
    if outputs != _OUTPUTS:
        raise PolicyBoundaryError("policy-boundary outputs are not frozen")
    _validate_learning(_mapping(value, "learning_policy"))
    _validate_coverage(_mapping(value, "coverage_policy"))
    _validate_uncertainty(_mapping(value, "uncertainty_policy"))
    _validate_sensitivity(_mapping(value, "sensitivity_policy"))
    _validate_support(_mapping(value, "support_requirements"))
    _validate_lineage(_mapping(value, "source_lineage"))
    _validate_execution(_mapping(value, "execution_policy"))


def _validate_axes(values: Sequence[object]) -> None:
    rows = tuple(_mapping_item(item, "boundary axis") for item in values)
    if tuple(_text(row, "axis") for row in rows) != _AXES:
        raise PolicyBoundaryError("policy-boundary axes are not frozen")
    if tuple(_text(row, "role") for row in rows) != _AXIS_ROLES:
        raise PolicyBoundaryError("policy-boundary axis roles are not frozen")
    if any(set(row) != {"axis", "role"} for row in rows):
        raise PolicyBoundaryError("policy-boundary axis fields mismatch")


def _validate_learning(value: Mapping[str, object]) -> None:
    if set(value) != {
        "model_family",
        "maximum_depth",
        "selection_objective",
        "predictive_accuracy_only",
    }:
        raise PolicyBoundaryError("policy-boundary learning fields mismatch")
    if (
        _text(value, "model_family") != "SHALLOW_AXIS_ALIGNED_RULE_TREE"
        or _integer(value, "maximum_depth") != 3
        or _text(value, "selection_objective") != "INTERPRETABILITY_WITH_EMPIRICAL_SUPPORT"
        or _bool(value, "predictive_accuracy_only")
    ):
        raise PolicyBoundaryError("policy-boundary learning policy is not frozen")


def _validate_coverage(value: Mapping[str, object]) -> None:
    if set(value) != {
        "minimum_strategy_classes",
        "minimum_records_per_strategy",
        "minimum_eligible_stability_cells",
        "unsupported_outcome",
    }:
        raise PolicyBoundaryError("policy-boundary coverage fields mismatch")
    if (
        _integer(value, "minimum_strategy_classes") != _MINIMUM_CLASSES
        or _integer(value, "minimum_records_per_strategy") != _MINIMUM_PER_STRATEGY
        or _integer(value, "minimum_eligible_stability_cells") != _MINIMUM_STABILITY_CELLS
        or _text(value, "unsupported_outcome") != "INSUFFICIENT_DATA"
    ):
        raise PolicyBoundaryError("policy-boundary coverage policy is not frozen")


def _validate_uncertainty(value: Mapping[str, object]) -> None:
    if set(value) != {"confidence_level", "interval", "bootstrap_resamples", "unit"}:
        raise PolicyBoundaryError("policy-boundary uncertainty fields mismatch")
    if (
        _number(value, "confidence_level") != 0.95
        or _text(value, "interval") != "PAIRED_BOOTSTRAP_PERCENTILE"
        or _integer(value, "bootstrap_resamples") != 2000
        or _text(value, "unit") != "paired_seed_regime_stream"
    ):
        raise PolicyBoundaryError("policy-boundary uncertainty policy is not frozen")


def _validate_sensitivity(value: Mapping[str, object]) -> None:
    if set(value) != {"analyses", "required_for_boundary"}:
        raise PolicyBoundaryError("policy-boundary sensitivity fields mismatch")
    analyses = tuple(
        _text_item(item, "sensitivity analysis") for item in _sequence(value, "analyses")
    )
    if analyses != (
        "LEAVE_ONE_REGIME_OUT",
        "THRESHOLD_PERTURBATION_PLUS_MINUS_10_PERCENT",
    ) or not _bool(value, "required_for_boundary"):
        raise PolicyBoundaryError("policy-boundary sensitivity policy is not frozen")


def _validate_support(value: Mapping[str, object]) -> None:
    if set(value) != {"required_fields", "source_status", "synthetic_substitution", "reason"}:
        raise PolicyBoundaryError("policy-boundary support requirement fields mismatch")
    fields = tuple(
        _text_item(item, "support field") for item in _sequence(value, "required_fields")
    )
    if fields != _SUPPORT:
        raise PolicyBoundaryError("policy-boundary support fields are not frozen")
    if _text(value, "source_status") != "INSUFFICIENT_DATA" or _bool(
        value, "synthetic_substitution"
    ):
        raise PolicyBoundaryError("policy-boundary support must remain fail-closed")
    _text(value, "reason")


def _validate_lineage(value: Mapping[str, object]) -> None:
    if set(value) != set(_SOURCE_DIGESTS):
        raise PolicyBoundaryError("policy-boundary lineage fields mismatch")
    for key, expected in _SOURCE_DIGESTS.items():
        digest = _text(value, key)
        if digest != expected or not _SHA256.fullmatch(digest):
            raise PolicyBoundaryError(f"policy-boundary {key} lineage is not frozen")


def _validate_execution(value: Mapping[str, object]) -> None:
    required = {
        "material_run_authorized",
        "r3_325_rerun",
        "write_external_artifacts",
        "synthetic_fill",
        "black_box_substitution",
        "predictive_accuracy_claim",
        "manifest_changes",
        "resource_envelope",
    }
    if set(value) != required:
        raise PolicyBoundaryError("policy-boundary execution fields mismatch")
    prohibited = (
        _bool(value, "material_run_authorized")
        or _bool(value, "r3_325_rerun")
        or _bool(value, "write_external_artifacts")
        or _bool(value, "synthetic_fill")
        or _bool(value, "black_box_substitution")
        or _bool(value, "predictive_accuracy_claim")
    )
    if prohibited:
        raise PolicyBoundaryError(
            "policy-boundary execution must remain read-only and interpretable"
        )
    if _text(value, "manifest_changes") != "NEW_VERSION_REQUIRED":
        raise PolicyBoundaryError("policy-boundary manifest change policy is not frozen")
    _text(value, "resource_envelope")


def _mapping(value: Mapping[str, object], key: str) -> Mapping[str, object]:
    return _mapping_item(value.get(key), key)


def _mapping_item(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise PolicyBoundaryError(f"{label} must be an object")
    return value


def _sequence(value: Mapping[str, object], key: str) -> Sequence[object]:
    selected = value.get(key)
    if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes, bytearray)):
        raise PolicyBoundaryError(f"{key} must be an array")
    return selected


def _text(value: Mapping[str, object], key: str) -> str:
    selected = value.get(key)
    if not isinstance(selected, str) or not selected.strip() or len(selected) > 1024:
        raise PolicyBoundaryError(f"{key} must be non-empty text")
    return selected


def _text_item(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PolicyBoundaryError(f"{label} must be non-empty text")
    return value


def _number(value: Mapping[str, object], key: str) -> float:
    selected = value.get(key)
    if isinstance(selected, bool) or not isinstance(selected, (int, float)):
        raise PolicyBoundaryError(f"{key} must be numeric")
    return float(selected)


def _integer(value: Mapping[str, object], key: str) -> int:
    selected = value.get(key)
    if isinstance(selected, bool) or not isinstance(selected, int):
        raise PolicyBoundaryError(f"{key} must be an integer")
    return selected


def _bool(value: Mapping[str, object], key: str) -> bool:
    selected = value.get(key)
    if not isinstance(selected, bool):
        raise PolicyBoundaryError(f"{key} must be boolean")
    return selected


__all__ = [
    "PolicyBoundaryAudit",
    "PolicyBoundaryError",
    "PolicyBoundaryPlan",
    "audit_policy_boundary_support",
    "load_policy_boundary_plan",
]
