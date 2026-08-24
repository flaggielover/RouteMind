from __future__ import annotations

from dataclasses import dataclass
from typing import Final, NoReturn


@dataclass(frozen=True, slots=True)
class ReasonCode:
    code: str
    category: str
    description: str


_DEFINITIONS = (
    ReasonCode(
        "CONFIG_INVALID", "configuration", "Pre-registration configuration is invalid"
    ),
    ReasonCode(
        "CONFIG_DIGEST_MISMATCH", "configuration", "Configuration digest changed"
    ),
    ReasonCode(
        "DIMENSION_INVALID", "numerics", "Vector or matrix dimension is invalid"
    ),
    ReasonCode("NONFINITE_VALUE", "numerics", "A numeric value is not finite"),
    ReasonCode("SINGULAR_MATRIX", "numerics", "A required matrix is singular"),
    ReasonCode(
        "UNKNOWN_NONLINEARITY", "configuration", "Nonlinearity is not pre-registered"
    ),
    ReasonCode(
        "OPEN_LOOP_UNSTABLE", "identification", "Estimated open loop is not stable"
    ),
    ReasonCode(
        "RANK_DEFICIENT", "identification", "Local excitation rank is deficient"
    ),
    ReasonCode(
        "CONDITION_EXCEEDED", "identification", "Gram conditioning exceeds the Gate"
    ),
    ReasonCode(
        "KAPPA_NOT_POSITIVE", "identification", "Estimated kappa is not positive"
    ),
    ReasonCode(
        "KAPPA_CI_CROSSES_ZERO", "identification", "Kappa interval is not positive"
    ),
    ReasonCode("KAPPA_CI_TOO_WIDE", "identification", "Kappa interval is too broad"),
    ReasonCode(
        "THRESHOLD_NONFINITE", "identification", "Threshold prediction is not finite"
    ),
    ReasonCode(
        "LOCAL_LINEARITY_DRIFT",
        "identification",
        "Local response changes across amplitudes",
    ),
    ReasonCode(
        "RESIDUAL_RMSE_EXCEEDED", "identification", "Normalized residual RMSE failed"
    ),
    ReasonCode(
        "RESIDUAL_AUTOCORRELATION",
        "identification",
        "Residual lag-one correlation failed",
    ),
    ReasonCode("RESIDUAL_MEAN_BIAS", "identification", "Residual mean bias failed"),
    ReasonCode("RESIDUAL_SCALE_TREND", "identification", "Residual scale trend failed"),
    ReasonCode("SYNTHETIC_A_RECOVERY", "identification", "Layer R A recovery failed"),
    ReasonCode("SYNTHETIC_M_RECOVERY", "identification", "Layer R M recovery failed"),
    ReasonCode(
        "SYNTHETIC_THRESHOLD_RECOVERY",
        "identification",
        "Layer R threshold error failed",
    ),
    ReasonCode(
        "SYNTHETIC_THRESHOLD_COVERAGE",
        "identification",
        "Layer R interval missed truth",
    ),
    ReasonCode(
        "ARTIFACT_ROOT_MISSING", "artifact", "ROUTEMIND_DATA_ROOT is not configured"
    ),
    ReasonCode(
        "ARTIFACT_PATH_UNSAFE", "artifact", "Artifact path escapes its class root"
    ),
    ReasonCode("ARTIFACT_EXISTS", "artifact", "Immutable artifact already exists"),
    ReasonCode(
        "ARTIFACT_DIGEST_MISMATCH", "artifact", "Artifact digest verification failed"
    ),
    ReasonCode(
        "ARTIFACT_CLASS_MISMATCH", "artifact", "Artifact class boundary was crossed"
    ),
    ReasonCode(
        "STAGE_ORDER_VIOLATION", "artifact", "A prerequisite frozen artifact is absent"
    ),
    ReasonCode(
        "LAYER_M_DEPENDENCY_VIOLATION",
        "architecture",
        "Layer M imports reduced internals",
    ),
)

REASON_CODES: Final[dict[str, ReasonCode]] = {item.code: item for item in _DEFINITIONS}

if len(REASON_CODES) != len(_DEFINITIONS):
    raise RuntimeError("reason-code registry contains duplicates")


class ResearchGateError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        reason = REASON_CODES.get(code)
        if reason is None:
            raise ValueError(f"unregistered reason code: {code}")
        self.reason = reason
        self.detail = detail.strip()
        suffix = f": {self.detail}" if self.detail else ""
        super().__init__(f"{reason.code}: {reason.description}{suffix}")


def fail(code: str, detail: str = "") -> NoReturn:
    raise ResearchGateError(code, detail)
