from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Literal

Metadata = tuple[tuple[str, str], ...]
ParameterType = Literal["float"]


@dataclass(frozen=True, slots=True)
class ParameterDefinition:
    key: str
    value_type: ParameterType
    default: str
    minimum: float | None = None
    maximum: float | None = None

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.default.strip():
            raise ValueError("parameter definition identity must not be blank")
        value = float(self.default)
        if not isfinite(value):
            raise ValueError("parameter default must be finite")
        if self.minimum is not None and value < self.minimum:
            raise ValueError("parameter default is below minimum")
        if self.maximum is not None and value > self.maximum:
            raise ValueError("parameter default is above maximum")


@dataclass(frozen=True, slots=True)
class StrategyParameterSchema:
    strategy: str
    version: str
    parameters: tuple[ParameterDefinition, ...] = ()

    def __post_init__(self) -> None:
        if not self.strategy.strip() or not self.version.strip():
            raise ValueError("parameter schema identity must not be blank")
        keys = [item.key for item in self.parameters]
        if len(keys) != len(set(keys)):
            raise ValueError("parameter keys must be unique")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "strategy": self.strategy,
            "version": self.version,
            "parameters": [
                {
                    "key": item.key,
                    "type": item.value_type,
                    "default": item.default,
                    "minimum": item.minimum,
                    "maximum": item.maximum,
                }
                for item in self.parameters
            ],
        }

    def validate(self, configuration: Metadata) -> Metadata:
        keys = [key for key, _ in configuration]
        if len(keys) != len(set(keys)):
            raise ValueError("parameter configuration keys must be unique")
        definitions = {item.key: item for item in self.parameters}
        unknown = sorted(set(keys) - definitions.keys())
        if unknown:
            raise ValueError(f"unknown strategy parameter: {unknown[0]}")
        values = dict(configuration)
        normalized: list[tuple[str, str]] = []
        for definition in self.parameters:
            raw = values.get(definition.key, definition.default)
            try:
                value = float(raw)
            except (TypeError, ValueError) as error:
                raise ValueError(f"parameter {definition.key} must be a finite float") from error
            if not isfinite(value):
                raise ValueError(f"parameter {definition.key} must be a finite float")
            if definition.minimum is not None and value < definition.minimum:
                raise ValueError(f"parameter {definition.key} is below minimum")
            if definition.maximum is not None and value > definition.maximum:
                raise ValueError(f"parameter {definition.key} is above maximum")
            normalized.append((definition.key, f"{value:.12g}"))
        return tuple(normalized)


def schema_for(strategy: str, version: str) -> StrategyParameterSchema:
    if strategy == "weighted-greedy":
        parameters: tuple[ParameterDefinition, ...] = (
            ParameterDefinition("distance_weight", "float", "1.0", 0.000001),
        )
    elif strategy == "risk-aware":
        parameters = tuple(
            ParameterDefinition(key, "float", default, 0.0)
            for key, default in (
                ("distance", "1.0"),
                ("readiness", "0.5"),
                ("overtime", "2.0"),
                ("service_risk", "2.0"),
                ("balance", "0.5"),
            )
        )
    else:
        parameters = ()
    return StrategyParameterSchema(strategy, version, parameters)
