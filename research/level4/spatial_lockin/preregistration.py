from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from .reason_codes import fail


def canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


def payload_digest(payload: object) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class Preregistration:
    path: Path
    payload: dict[str, object]
    digest: str

    @classmethod
    def load(cls, path: Path) -> Preregistration:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            fail("CONFIG_INVALID", str(exc))
        if not isinstance(payload, dict):
            fail("CONFIG_INVALID", "pre-registration root must be an object")
        instance = cls(path.resolve(), payload, payload_digest(payload))
        instance.validate()
        return instance

    def require(self, key: str, expected_type: type[object]) -> object:
        value = self.payload.get(key)
        if not isinstance(value, expected_type):
            fail("CONFIG_INVALID", f"{key} has invalid type")
        return value

    def validate(self) -> None:
        if self.payload.get("schema_version") != 1:
            fail("CONFIG_INVALID", "unsupported schema version")
        if self.payload.get("experiment_id") != "routemind-level4-spatial-lockin-v1":
            fail("CONFIG_INVALID", "unexpected experiment identity")
        identification = cast(dict[str, object], self.require("identification", dict))
        validation = cast(dict[str, object], self.require("validation", dict))
        nonlinearities = cast(list[object], self.require("nonlinearities", list))
        gates = cast(dict[str, object], self.require("gates", dict))
        if identification.get("horizon") != 12:
            fail("CONFIG_INVALID", "identification horizon changed")
        if identification.get("feedback_settings") != [0.0, 0.35]:
            fail("CONFIG_INVALID", "feedback settings changed")
        if identification.get("seeds") != list(range(11000, 11064)):
            fail("CONFIG_INVALID", "identification seeds changed")
        if validation.get("seeds") != list(range(21000, 21064)):
            fail("CONFIG_INVALID", "validation seeds changed")
        if nonlinearities != ["tanh", "logistic", "clipped_linear", "atan"]:
            fail("CONFIG_INVALID", "nonlinearity family changed")
        required_gates = {
            "condition_number_max",
            "spectral_radius_max",
            "kappa_ci_relative_width_max",
            "local_linearity_drift_max",
            "residual_nrmse_max",
            "residual_autocorrelation_max",
            "residual_mean_sd_max",
            "layer_r_a_relative_error_max",
            "layer_r_m_relative_error_max",
            "layer_r_threshold_relative_error_max",
        }
        if not required_gates.issubset(gates):
            fail("CONFIG_INVALID", "required Gate thresholds are missing")
